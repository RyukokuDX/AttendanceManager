#/api/projects/{project_number}/{researcher_number}/allocations


# {{{ import
from fastapi import FastAPI, HTTPException, Path, File, UploadFile, Depends, Body
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import sqlite3
import os
import logging
import httpx
from xml.etree import ElementTree as ET
import base64
import json
import re
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List, Optional
from models.models import Student, AttendanceLog, CurrentStatus, Alert
from schemas.schemas import StudentCreate, Student as StudentSchema, AttendanceLogCreate, AttendanceLog as AttendanceLogSchema, CurrentStatusCreate, CurrentStatus as CurrentStatusSchema, AlertCreate, Alert as AlertSchema, AttendanceResponse, CoreTimeUpdate
from db.database import get_db
# }}}

app = FastAPI(title="Attendance Manager API")

# CORSミドルウェアの設定
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # 本番環境では適切に制限してください
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# 静的ファイルの設定（APIエンドポイントの後にマウント）
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("../public/index.html", "r", encoding="utf-8") as f:
        return f.read()

#{{{ ロギングの設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.info("Start FastAPI")
#}}}

#{{{ # データベース接続
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "db/Attendance2025.db")

def get_db_connection():
	""" データベース接続を確立 """
	if not os.path.exists(DATABASE):
		logger.error(f"Nonexist: {DATABASE}")
		raise FileNotFoundError(f"Not exist: {DATABASE}")

	try:
		logger.info(f"Open Database: {DATABASE}")
		conn = sqlite3.connect(DATABASE)
		conn.row_factory = sqlite3.Row
		return conn
	except sqlite3.Error as e:
		logger.error(f"DB Error: {e}")
		raise HTTPException(status_code=500, detail="データベースに接続できませんでした")
#}}}

#{{{ 学生管理API
@app.post("/api/students/", response_model=StudentSchema)
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
	db_student = Student(**student.dict())
	db.add(db_student)
	db.commit()
	db.refresh(db_student)
	return db_student

@app.get("/api/students/", response_model=List[StudentSchema])
def read_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
	students = db.query(Student).offset(skip).limit(limit).all()
	return students

@app.get("/api/students/{student_id}", response_model=StudentSchema)
def read_student(student_id: str, db: Session = Depends(get_db)):
	student = db.query(Student).filter(Student.student_id == student_id).first()
	if student is None:
		raise HTTPException(status_code=404, detail="Student not found")
	return student

@app.delete("/api/students/{student_id}")
async def delete_student(
    student_id: str,
    db: Session = Depends(get_db)
):
    """
    指定された学籍番号の学生のレコードを削除するAPI
    関連する出席記録、現在の入室状況、コアタイム違反の記録も削除します
    """
    try:
        # トランザクション開始
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # 関連する出席記録を削除
        db.query(AttendanceLog).filter(
            AttendanceLog.student_id == student_id
        ).delete()

        # 現在の入室状況を削除
        db.query(CurrentStatus).filter(
            CurrentStatus.student_id == student_id
        ).delete()

        # コアタイム違反の記録を削除
        db.query(Alert).filter(
            Alert.student_id == student_id
        ).delete()

        # 学生レコードを削除
        db.delete(student)

        # 変更をコミット
        db.commit()

        # Telegram通知を送信
        message = f"🗑️ {student.name}さん（学籍番号：{student_id}）のレコードを削除しました。"
        await send_telegram_message(message)

        return {"status": "success", "message": f"学生ID {student_id} のレコードを削除しました"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"学生削除エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
#}}}

#{{{ 入退室管理API
@app.post("/api/attendance/", response_model=AttendanceResponse)
def record_attendance(attendance: AttendanceLogCreate, db: Session = Depends(get_db)):
	# 学生が存在するか確認
	student = db.query(Student).filter(Student.student_id == attendance.student_id).first()
	if student is None:
		raise HTTPException(status_code=404, detail="Student not found")

	# 現在の入室状況を確認
	current_status = db.query(CurrentStatus).filter(
		CurrentStatus.student_id == attendance.student_id
	).first()

	if current_status is None:
		# 入室処理
		db_attendance = AttendanceLog(
			student_id=attendance.student_id,
			entry_time=attendance.time,
			exit_time=None  # 明示的にNoneを設定
		)
		db.add(db_attendance)
		
		# 現在の入室状況を更新
		current_status = CurrentStatus(
			student_id=attendance.student_id,
			entry_time=attendance.time
		)
		db.add(current_status)
		db.commit()
		return {"name": student.name, "status": "入室"}
	else:
		# 退室処理
		# 既存の入室記録を更新
		attendance_log = db.query(AttendanceLog).filter(
			AttendanceLog.student_id == attendance.student_id,
			AttendanceLog.exit_time.is_(None)  # exit_timeがNullのレコードを検索
		).order_by(AttendanceLog.entry_time.desc()).first()  # 最新の記録を取得
		
		if attendance_log:
			attendance_log.exit_time = attendance.time
		
		# 現在の入室状況を削除
		db.delete(current_status)
		db.commit()
		return {"name": student.name, "status": "退室"}

@app.get("/api/attendance/{student_id}", response_model=List[AttendanceLogSchema])
def read_student_attendance(
	student_id: str,
	days: int = 0,  # 日数パラメータを追加（デフォルトは0）
	db: Session = Depends(get_db)
):
	# 基本のクエリを作成
	query = db.query(AttendanceLog).filter(
		AttendanceLog.student_id == student_id
	)
	
	# 日数が0より大きい場合、指定された日数分のレコードを取得
	if days > 0:
		# 現在時刻から指定された日数分前の日時を計算
		cutoff_date = datetime.now() - timedelta(days=days)
		query = query.filter(AttendanceLog.entry_time >= cutoff_date)
	
	# レコードを取得（入室時刻の降順でソート）
	attendance_logs = query.order_by(AttendanceLog.entry_time.desc()).all()
	return attendance_logs

@app.get("/api/current-status/", response_model=List[CurrentStatusSchema])
def read_current_status(db: Session = Depends(get_db)):
	current_status = db.query(CurrentStatus).all()
	return current_status

@app.post("/api/attendance-now/{student_id}", response_model=AttendanceResponse)
async def record_attendance_now(
	student_id: str,
	db: Session = Depends(get_db)
):
	"""
	現在時刻を使用して入退室を記録するエンドポイント
	"""
	# 現在時刻を取得
	current_time = datetime.now()
	
	# 学生の存在確認
	student = db.query(Student).filter(Student.student_id == student_id).first()
	if not student:
		raise HTTPException(status_code=404, detail="Student not found")
	
	# 現在の入室状況を確認
	current_status = db.query(CurrentStatus).filter(
		CurrentStatus.student_id == student_id
	).first()
	
	if not current_status:
		# 入室処理
		current_status = CurrentStatus(
			student_id=student_id,
			entry_time=current_time
		)
		db.add(current_status)
		
		# 出席ログに記録
		attendance_log = AttendanceLog(
			student_id=student_id,
			entry_time=current_time,
			exit_time=None
		)
		db.add(attendance_log)
		
		db.commit()

		# Telegram通知を送信
		message = f"🟢 {student.name}さんが入室しました。\n時刻: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
		await send_telegram_message(message)
		
		return AttendanceResponse(name=student.name, status="入室")
	else:
		# 退室処理
		# 出席ログを更新
		attendance_log = db.query(AttendanceLog).filter(
			AttendanceLog.student_id == student_id,
			AttendanceLog.exit_time == None
		).order_by(AttendanceLog.entry_time.desc()).first()
		
		if attendance_log:
			attendance_log.exit_time = current_time
		
		# 現在の入室状況を削除
		db.delete(current_status)
		db.commit()

		# Telegram通知を送信
		message = f"🔴 {student.name}さんが退室しました。\n時刻: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
		await send_telegram_message(message)
		
		return AttendanceResponse(name=student.name, status="退室")

@app.post("/api/reset-status")
async def reset_status(db: Session = Depends(get_db)):
    """
    全学生の入室状況をリセットするAPI
    CurrentStatusテーブルのレコードをすべて削除します
    """
    try:
        # 現在の入室状況を取得（ログ用）
        current_statuses = db.query(CurrentStatus).join(
            Student,
            CurrentStatus.student_id == Student.student_id
        ).with_entities(
            Student.name,
            Student.student_id,
            CurrentStatus.entry_time
        ).all()
        
        if current_statuses:
            # リセットされる学生の名前リストを作成
            student_details = [
                f"・{name}さん（学籍番号：{student_id}）" 
                for name, student_id, _ in current_statuses
            ]
            student_list = "\n".join(student_details)
            
            # すべての入室状況レコードを削除
            db.query(CurrentStatus).delete()
            
            # 変更をコミット
            db.commit()
            
            # Telegram通知を送信
            message = (
                f"🔄 入室状況をリセットしました。\n\n"
                f"リセットされた学生:\n{student_list}"
            )
            await send_telegram_message(message)
            
            return {
                "status": "success",
                "message": "入室状況をリセットしました。",
                "reset_students": student_details
            }
        else:
            message = "リセット対象の学生はいませんでした。"
            await send_telegram_message(message)
            return {
                "status": "success",
                "message": message,
                "reset_students": []
            }
            
    except Exception as e:
        db.rollback()
        logger.error(f"入室状況リセットエラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"入室状況のリセット中にエラーが発生しました: {str(e)}"
        )
#}}}

#{{{ コアタイム管理API
@app.get("/api/core-time/check/{period}")
async def check_core_time(period: int, db: Session = Depends(get_db)):
    try:
        current_time = datetime.now()
        current_day = current_time.weekday() + 1  # 1:月曜 2:火曜 ... 7:日曜
        
        # コアタイムの学生を取得
        students = db.query(Student).filter(
            ((Student.core_time_1_day == current_day) & (Student.core_time_1_period == period)) |
            ((Student.core_time_2_day == current_day) & (Student.core_time_2_period == period))
        ).all()

        violations = []
        for student in students:
            # 入室状況を確認
            current_status = db.query(CurrentStatus).filter(
                CurrentStatus.student_id == student.student_id
            ).first()
            
            if not current_status:
                # コアタイム違反
                violations.append(student.student_id)

                # 同じ日の同じ時限の違反が既に記録されているか確認
                existing_alert = db.query(Alert).filter(
                    Alert.student_id == student.student_id,
                    Alert.alert_date == current_time.date(),
                    Alert.alert_period == period
                ).first()

                # 重複がない場合のみアラートを記録
                if not existing_alert:
                    alert = Alert(
                        student_id=student.student_id,
                        alert_date=current_time.date(),
                        alert_period=period
                    )
                    db.add(alert)
                    db.commit()

                    # Telegram通知を送信
                    message = (
                        f"⚠️ コアタイム違反の通知\n\n"
                        f"学籍番号: {student.student_id}\n"
                        f"氏名: {student.name}\n"
                        f"違反日時: {current_time.strftime('%Y-%m-%d')} {period}限目"
                    )
                    await send_telegram_message(message)

            # 違反回数を更新 （試験的に全学生に対して実行)
            # student.core_time_violations を Alertのstudent_idでカウント
            violation_count = db.query(Alert).filter(
                Alert.student_id == student.student_id
            ).count()
            student.core_time_violations = violation_count
            db.add(student)
            db.commit()


        # 更新後の学生データを取得して返す
        updated_students = db.query(Student).filter(
            Student.student_id.in_([s.student_id for s in students])
        ).all()
        
        return {
            "violations": violations,
            "updated_students": [
                {
                    "student_id": s.student_id,
                    "core_time_violations": s.core_time_violations
                } for s in updated_students
            ]
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/core-time/violations", response_model=List[AlertSchema])
def read_core_time_violations(db: Session = Depends(get_db)):
    try:
        alerts = db.query(Alert).all()
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
#}}}

#{{{ コアタイム設定API
@app.post("/api/coretime/{student_id}")
async def set_coretime(
    student_id: str,
    coretime: CoreTimeUpdate,
    db: Session = Depends(get_db)
):
    try:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student.core_time_1_day = coretime.core_time_1_day
        student.core_time_1_period = coretime.core_time_1_period
        student.core_time_2_day = coretime.core_time_2_day
        student.core_time_2_period = coretime.core_time_2_period
        
        db.commit()
        return {"message": "Core time updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/coretime/{student_id}")
async def get_coretime(
    student_id: str,
    db: Session = Depends(get_db)
):
    """
    学生のコアタイム設定を取得するAPI
    """
    try:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        return {
            "core_time_1_day": student.core_time_1_day,
            "core_time_1_period": student.core_time_1_period,
            "core_time_2_day": student.core_time_2_day,
            "core_time_2_period": student.core_time_2_period
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"コアタイム取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
#}}}

# 静的ファイルの設定（最後にマウント）
app.mount("/js", StaticFiles(directory="../public/js"), name="js")
app.mount("/", StaticFiles(directory="../public", html=True), name="static")

# Telegram設定
class Settings(BaseSettings):
    telegram_id: str
    telegram_alert: str

    class Config:
        env_file = ".env"

settings = Settings()

async def send_telegram_message(message: str) -> bool:
    """
    Telegramにメッセージを送信する関数
    """
    try:
        url = f"https://api.telegram.org/bot{settings.telegram_alert}/sendMessage"
        data = {
            "chat_id": settings.telegram_id,
            "text": message,
            "parse_mode": "HTML"
        }
        logging.info(f"Telegram送信試行: URL={url}, データ={data}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            logging.info(f"Telegram送信レスポンス: {response.status_code} - {response.text}")
            return response.status_code == 200
    except Exception as e:
        logging.error(f"Telegram送信エラー: {str(e)}")
        return False
