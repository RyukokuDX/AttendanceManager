# -*- coding: utf-8 -*-
#
#2023/12/19: 何故か前回に読み込んだIDを削除する挙動があったため, 削除の確認ボタンを追加
#2023/12/21: 全体の記録をとっていなかったのでとる
#

# {{{ Librarlies
import tkinter as tk
from tkinter import ttk
from tkinter import font
import nfc
import time
import threading
import json
import requests
from ID_handelr import remove_register
from ID_handelr import add_entry
from ID_handelr import update_entry
from ID_handelr import read_entry
#}}}

# {{{ global 変数の用意
key_id = None
file_path = "List"
record_path = "Record"
entry_number = None
entry_name = None
# 登録名入力待ちの判定
on_going_register = False
# Debug 用の停止命令
close_order = False
# }}}

#{{{ Tkinter ウィンドウの作成と準備
root = tk.Tk()
root.title("ver 0.1")

# 全画面表示
root.attributes('-fullscreen',True)
root.configure(bg="black")

# ウィンドウ全体のパディング
root['padx'] = 100
root['pady'] = 100

# ウィンドウの幅と高さを取得
window_width = root.winfo_reqwidth()
window_height = root.winfo_reqheight()
#}}}

# {{{ フォントの設定
default_font = font.nametofont("TkDefaultFont")
default_font.configure(family="BIZ UDPMincho", size=22)
title_font=("BIZ UDPMincho", 28)
style = ttk.Style()
style.configure("TRadiobutton", padding=15, foreground="green", background="black", size=22)
# }}}

#{{{ IO関連の準備
system_message1 = tk.StringVar()
system_message2 = tk.StringVar()

system_message1.set("システム: 現在, 入退室記録モードです.")
system_message2.set("システム: 学生証を読み込んでください.")

def message_timelog_mode():
    # 入退室記録モードに変更時のメッセージ
    system_message1.set("システム: 現在, 入退室記録モードです.")
    system_message2.set("システム: 学生証を読み込んでください.")

def message_register_mode():
    # 登録情報編集モードに変更時のメッセージ
    system_message1.set("システム: 現在, 登録情報編集モードです.")
    system_message2.set("システム: 学生証を読み込んでください.")

entry_width = window_width // 3
entry = tk.Entry(root, width=entry_width)
#}}}

#{{{ def register_entry():
def register_entry():
    # Entry登録追加ボタンの処理
    global file_path
    entry_name = entry.get()
    if entry_name == "":
        system_message1.set("システム: エラー: 登録名が確認できませんでした")
        system_message2.set("システム: 学生証を読み直してください")
        entry.delete(0, tk.END)
        entry.grid_remove()
        register_button.grid_remove()
        root.after(2500,message_register_mode)
    else:
        add_entry(file_path, key_id, entry_name)
        message = "システム: " +  entry_name + " さんを登録しました"
        system_message2.set(message)
        entry.delete(0, tk.END)
        entry.grid_remove()
        register_button.grid_remove()
        root.after(2500,message_register_mode)

    # 登録が入力が終わったことを伝える
    global on_going_register
    on_going_register = False

    radio_button1.grid(row=1, column=1,pady=20)
#}}}

#{{{ def delete_cancel():
def delete_cancel():
    global entry_name

    # ボタン削除
    delete_button.grid_remove()
    cancel_button.grid_remove()

    message = "システム: " +  entry_name + " さんの登録を保持します"
    system_message2.set(message)

    root.after(1500,message_register_mode)

    # モード変更ボタンの再表示
    radio_button1.grid(row=1, column=1,pady=20)

    global on_going_register
    on_going_register = False
#}}}

#{{{ def delete_register()
def delete_register():
    global file_path
    global entry_name
    global entry_number

    # ボタン削除
    delete_button.grid_remove()
    cancel_button.grid_remove()

    remove_register(file_path,entry_number)

    message = "システム: " +  entry_name + " さんの登録を削除しました"
    system_message2.set(message)

    root.after(1500,message_register_mode)

    # モード変更ボタンの再表示
    radio_button1.grid(row=1, column=1,pady=20)

    global on_going_register
    on_going_register = False
#}}}

#{{{ def window_close()
def window_close():
    global close_order
    close_order = True
    root.destroy()
#}}}

# {{{ def webhook_post():
def webhook_post(webhook_title, webhook_message):
    webhook_address = "https://ryu365.webhook.office.com/webhookb2/585cc2b0-ed47-41cd-8bd1-39b5befc07b2@23b65fdf-a4e3-4a19-b03d-12b1d57ad76e/IncomingWebhook/eee629f8a82b4427baf47019708e6b1b/3662ba78-b3f0-47e3-9820-376798dc17d5"
    post_json = json.dumps(
        {
            'title': webhook_title,
            'text': webhook_message
        }
    )
    requests.post(webhook_address, post_json)
#}}}

# {{{ Tkinter Windowの設置
# ラジオボタン選択された値を保持するための変数
current_mode = tk.StringVar()

# デフォルトの選択値を設定
current_mode.set("Log")

radio_button1 = ttk.Radiobutton(root, text="入退室記録モード",
        variable=current_mode,
        value="Log",
        width=20,
        command=message_timelog_mode)
radio_button2 = ttk.Radiobutton(root, text="登録情報編集モード",
        variable=current_mode,
        value="Register",
        width=20,
        command=message_register_mode)

# 登録ボタンの設定
register_button = tk.Button(root, text="登録", command=register_entry)
close_button = tk.Button(root, text="Close", command=window_close)
delete_button = tk.Button(root, text="削除", command=delete_register)
cancel_button = tk.Button(root, text="取消", command=delete_cancel)


# tkinterに配置
title = tk.Label(root, text="藤原和将研究室 入退室管理ソフト", font=title_font, foreground="green", bg="black")
title.grid(column=0, row=0, columnspan=3)
radio_button1.grid(row=1, column=1,pady=20)
radio_button2.grid(row=1, column=2)
system_output1 = tk.Label(root, textvariable=system_message1, foreground="green", bg="black", pady=10)
system_output2 = tk.Label(root, textvariable=system_message2, foreground="green", bg="black", pady=10)
system_output1.grid(row=2, column=0, columnspan=3, sticky=tk.W)
system_output2.grid(row=3, column=0, columnspan=3, sticky=tk.W)
# Debug 用
# close_button.grid(row=9, column=1)

# 列ごとの幅指定
root.columnconfigure(0, weight=2)
root.columnconfigure(1, weight=1)
root.columnconfigure(2, weight=1)
# }}}

# {{{  def on_connect(tag):
def on_connect(tag):
    # nfc カード接続時のid読み取り(小文字)
    global key_id
    key_id=tag.identifier.hex()
#}}}

# {{{ def nfc_register():
def nfc_register():
    #global 変数の読み込み
    global file_path
    global record_path
    global key_id
    global current_mode
    global on_going_register
    global close_order
    global entry_number
    global entry_name

    # nfc カードの読み込み用意
    clf = nfc.ContactlessFrontend('usb')
    # カード接続時にidのみを読み取り
    #  clf.connect(rdwr={'on-connect': on_connect})
    # terminate を指定しないと, 読み取りを中断できない
    clf.connect(rdwr={'on-connect': on_connect}, terminate=lambda: close_order)

    # List から該当のidがあるか判定
    # entry_number は該当がなければ-1, あれば行数-1をかえす
    # entry_name は該当があれば登録名を返す
    entry_number, entry_name = read_entry(file_path, key_id)

    # 入退室記録モードの場合
    if current_mode.get() == "Log":

        # 登録がない場合の処理
        if entry_number == -1:
            # メッセージを表示して読み取り再開
            system_message1.set("システム: 登録のない学生証が読みこまれました")
            system_message2.set("システム: 入退室情報を記録するためには，まず登録をしてください")
            root.after(2500,message_timelog_mode)

        # 登録がない場合の処理
        else:
            system_message1.set("システム: 登録のある学生証が読みこまれました")

            # statusは更新された登録行の名前以外の値をタブ区切りでリストにしたもの
            # status[0]: 1 : 入室 : 0 : 退室
            # status[1]: 在室時間の時間数 : 入室時は0となっている
            # status[2]: 在室時間の分数 : 入室時は0となっている
            status = update_entry(file_path, key_id)
            add_record(record_path, entry_name, status[0])

            if status[0]:
                message = "システム: " +  entry_name + " さんようこそ"
                system_message2.set(message)
                webhook_title = entry_name
                webhook_message = "入室"
                webhook_post(webhook_title, webhook_message)

                # 入室時は多分メッセージを読まないので，１秒
                root.after(1000,message_timelog_mode)
            else:
                message = "システム: " +  entry_name + " さん さようなら在室時間は" + str(status[1]) + "時間" + str(status[2]) + "分でした"
                system_message2.set(message)
                webhook_title = entry_name
                webhook_message = "退室: 在室時間は" + str(status[1]) + "時間" + str(status[2]) + "分"
                webhook_post(webhook_title, webhook_message)
                root.after(2500,message_timelog_mode)

    # 登録モードの場合
    else:

        # 登録作業に入るため, 他の作業を受け付けないフラグを立てる
        on_going_register = True

        # 登録があるか調べる
        if entry_number == -1:

            # 氏名入力中にモード変更させない
            radio_button1.grid_remove()

            system_message1.set("システム: 登録のない学生証が読みこまれました")
            system_message2.set("システム: 登録名を入力して登録してください")
            entry.grid(row=4, column=0, columnspan=2, pady=15, sticky="e")
            register_button.grid(row=4, column=2, sticky="w", padx=10)
        else:
            # 氏名入力中にモード変更させない
            radio_button1.grid_remove()

            system_message1.set("システム: 登録のある学生証が読みこまれました")

            message = "システム: " +  entry_name + " さんの登録を削除しますか？"
            system_message2.set(message)

            delete_button.grid(row=4, column=1)
            cancel_button.grid(row=4, column=2)

    clf.close()

    # 登録名の入力待機
    # entry_register 内でglobal変数のon_going_registerがFalseになるまで待機する.
    # 上のif内に書いたほうがいいかもしれないがclfはこの段階で閉じて良いのでここに配置した.
    try:
        while on_going_register:
            time.sleep(1)
    except KeyboardInterrupt:
        close_order = True

    if not close_order:
        root.after(1000,nfc_read)
#}}}

#{{{ def nfc_read():
# nfcカード読み取り用のスレッドを起動する.
# スレッドを別にしないとUIの操作よりもカード読み取り待機が優先されて操作ができない
def nfc_read():
    # nfc.readの待機状態を外部から中断するために工夫が必要か
    nfc_thread = threading.Thread(target=nfc_register)
    nfc_thread.start()
nfc_read()
#}}}

# ウィンドウを表示
root.mainloop()
