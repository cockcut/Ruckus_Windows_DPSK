# -*- coding: utf-8 -*-
"""
HSITX Ruckus DPSK Tool - GUI
SmartZone / Unleashed DPSK + GitHub 업데이트
"""

import os
import sys
import csv
import shutil
import threading
import queue
from datetime import datetime
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Button, Entry, Scrollbar, Canvas, StringVar,
    LabelFrame, filedialog, messagebox, ttk, END, BOTH, X, Y, LEFT, RIGHT,
    DISABLED, NORMAL, HORIZONTAL, VERTICAL,
)

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
    sys.path.insert(0, str(Path(getattr(sys, "_MEIPASS", ROOT))))
else:
    ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from modules.sz_api import CONTROLLER_API_MAP, SmartZoneAPI
from modules.unleashed_api import UnleashedAPI
from modules import updater as gh_updater

RESULTS_DIR = ROOT / "results"
RESULTS_DPSK = RESULTS_DIR / "dpsk"
RESULTS_UDPSK = RESULTS_DIR / "dpsk_ul"
for _d in (RESULTS_DIR, RESULTS_DPSK, RESULTS_UDPSK):
    _d.mkdir(exist_ok=True)

APP_VERSION = "0.0.1"
APP_TITLE = f"HSITX Ruckus DPSK Tool v{APP_VERSION}"
BG = "#f4f4f9"
CARD = "#ffffff"
ACCENT = "#d9534f"
BTN_BG = "#f8f9fa"
BTN_ACTIVE = "#e2e6ea"
LINK = "#007bff"


class App(Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x760")
        self.minsize(860, 640)
        self.configure(bg=BG)
        self._log_queue = queue.Queue()
        self._worker = None
        self._stop_flag = False
        self._update_info = None
        self._build_main()
        threading.Thread(target=self._check_github_update, daemon=True).start()

    def _clear_page(self):
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass
        for w in self.winfo_children():
            w.destroy()
        try:
            self.geometry("1180x760")
        except Exception:
            pass

    def _build_main(self):
        self._clear_page()
        outer = Frame(self, bg=BG, padx=24, pady=20)
        outer.pack(fill=BOTH, expand=True)
        Label(outer, text=APP_TITLE, font=("Segoe UI", 18, "bold"), fg=ACCENT, bg=BG).pack(anchor="w")
        Label(
            outer,
            text=f"버전 {APP_VERSION}  |  SmartZone / Unleashed DPSK",
            font=("Segoe UI", 9), fg="#666", bg=BG,
        ).pack(anchor="w", pady=(4, 8))
        upd_row = Frame(outer, bg=BG)
        upd_row.pack(anchor="w", pady=(0, 12))
        self._upd_check_btn = Button(
            upd_row, text="업데이트 확인", font=("Segoe UI", 9, "bold"),
            bg="#fff", fg=ACCENT, relief="solid", borderwidth=1,
            highlightbackground=ACCENT, padx=10, pady=2,
            command=self._manual_github_check, cursor="hand2",
        )
        self._upd_check_btn.pack(side=LEFT)
        self._upd_btn = Button(
            upd_row, text="업데이트", font=("Segoe UI", 9, "bold"),
            bg=ACCENT, fg="white", relief="flat", padx=12, pady=2,
            command=self._do_github_update, cursor="hand2",
        )
        self._upd_status = StringVar(value="")
        Label(upd_row, textvariable=self._upd_status, font=("Segoe UI", 9), fg="#666", bg=BG).pack(side=LEFT, padx=(10, 0))
        info = getattr(self, "_update_info", None) or {}
        if info.get("available"):
            if info.get("frozen"):
                self._upd_status.set("GitHub에 새 exe가 있습니다.")
            else:
                self._upd_status.set("GitHub에 새 버전이 있습니다.")
            self._upd_btn.pack(side=LEFT, padx=(10, 0))
        elif info.get("ok"):
            self._upd_status.set("최신 버전입니다.")
            self._upd_btn.pack_forget()
        elif info.get("message"):
            self._upd_status.set(str(info.get("message")))
            self._upd_btn.pack_forget()
        else:
            self._upd_btn.pack_forget()

        wrap = Frame(outer, bg=BG)
        wrap.pack(fill=BOTH, expand=True)
        canvas = Canvas(wrap, bg=CARD, highlightthickness=0)
        sb = Scrollbar(wrap, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        sb.pack(side=RIGHT, fill=Y)
        card = Frame(canvas, bg=CARD, padx=20, pady=16)
        win = canvas.create_window((0, 0), window=card, anchor="nw")

        def _main_cfg(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(win, width=canvas.winfo_width())
        card.bind("<Configure>", _main_cfg)
        canvas.bind("<Configure>", _main_cfg)

        def _mw(event):
            if not canvas.winfo_exists():
                try:
                    canvas.unbind_all("<MouseWheel>")
                except Exception:
                    pass
                return
            canvas.yview_scroll(-1 if getattr(event, "delta", 0) > 0 else 1, "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _mw))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        for num, title in (
            ("1", "SmartZone DPSK 관리"),
            ("2", "Unleashed DPSK 관리"),
        ):
            self._menu_btn(card, f"[ {num}. {title} ]", True, num)

    def _menu_btn(self, parent, text, enabled, num):
        b = Button(
            parent,
            text=text + "  ★",
            font=("Segoe UI", 11),
            bg=BTN_BG if enabled else "#eee",
            fg=LINK if enabled else "#999",
            activebackground=BTN_ACTIVE,
            relief="solid",
            borderwidth=1,
            anchor="w",
            padx=14, pady=8,
            cursor="hand2" if enabled else "arrow",
            command=(lambda n=num: self._on_menu(n)) if enabled else None,
            state=NORMAL if enabled else DISABLED,
        )
        b.pack(fill=X, pady=4)

    def _manual_github_check(self):
        if hasattr(self, "_upd_status"):
            self._upd_status.set("GitHub 확인 중...")
        if hasattr(self, "_upd_check_btn"):
            self._upd_check_btn.config(state=DISABLED)
        threading.Thread(target=self._check_github_update, daemon=True).start()

    def _check_github_update(self):
        frozen = bool(getattr(sys, "frozen", False))
        info = gh_updater.check_update(ROOT, frozen=frozen, current_version=APP_VERSION)
        self._update_info = info
        self.after(0, lambda: self._show_update_ui(info))

    def _show_update_ui(self, info: dict):
        if hasattr(self, "_upd_check_btn"):
            try:
                self._upd_check_btn.config(state=NORMAL)
            except Exception:
                pass
        if not info or not hasattr(self, "_upd_status"):
            return
        if not info.get("ok"):
            self._upd_status.set(info.get("message") or "업데이트 확인 실패")
            if hasattr(self, "_upd_btn"):
                self._upd_btn.pack_forget()
            return
        if info.get("available"):
            if info.get("frozen"):
                self._upd_status.set("GitHub에 새 exe가 있습니다.")
            else:
                self._upd_status.set("GitHub에 새 버전이 있습니다.")
            if hasattr(self, "_upd_btn") and not self._upd_btn.winfo_ismapped():
                self._upd_btn.pack(side=LEFT, padx=(10, 0))
        else:
            self._upd_status.set("최신 버전입니다.")
            if hasattr(self, "_upd_btn"):
                self._upd_btn.pack_forget()

    def _do_github_update(self):
        info = getattr(self, "_update_info", None) or {}
        frozen = bool(getattr(sys, "frozen", False))
        if frozen:
            msg = "GitHub에서 새 exe를 받아 지금 실행 파일을 교체할까요?"
        else:
            msg = "GitHub에서 최신 소스를 받아 덮어쓸까요?\nresults 폴더는 유지됩니다."
        if not messagebox.askyesno("업데이트", msg):
            return
        self._upd_status.set("업데이트 받는 중...")
        self._upd_btn.config(state=DISABLED)

        def work():
            result = gh_updater.apply_update(
                ROOT,
                expected_sha=info.get("remote") or "",
                frozen=frozen,
                exe_path=sys.executable if frozen else "",
                info=info,
            )
            self.after(0, lambda: self._after_github_update(result))

        threading.Thread(target=work, daemon=True).start()

    def _after_github_update(self, result: dict):
        if hasattr(self, "_upd_btn"):
            self._upd_btn.config(state=NORMAL)
        if result.get("ok"):
            bat = result.get("replace_bat")
            if bat:
                messagebox.showinfo("완료", result.get("message") or "exe 업데이트 준비됨")
                try:
                    import subprocess
                    env = os.environ.copy()
                    for k in list(env):
                        if k.startswith("_PYI") or k in ("PYTHONHOME", "PYTHONPATH"):
                            env.pop(k, None)
                    subprocess.Popen(["cmd", "/c", bat], cwd=str(ROOT), env=env, close_fds=True)
                except Exception as e:
                    messagebox.showerror("업데이트", f"교체 스크립트 실행 실패:\n{e}")
                    return
            else:
                messagebox.showinfo("완료", result.get("message") or "업데이트 완료")
            self.destroy()
        else:
            if hasattr(self, "_upd_status"):
                self._upd_status.set("업데이트 실패")
            messagebox.showerror("업데이트 실패", result.get("message") or "실패")

    def _on_menu(self, num):
        if num == "1":
            self._build_dpsk()
        elif num == "2":
            self._build_uldpsk()

    def _back_btn(self, parent):
        Button(
            parent, text="← 메인 메뉴", font=("Segoe UI", 10),
            bg=BTN_BG, relief="solid", borderwidth=1, padx=10, pady=4,
            command=self._build_main, cursor="hand2",
        ).pack(anchor="w", pady=(0, 10))

    def _build_dpsk(self):
        self._clear_page()
        outer = Frame(self, bg=BG, padx=12, pady=10)
        outer.pack(fill=BOTH, expand=True)
        top = Frame(outer, bg=BG)
        top.pack(fill=X)
        self._back_btn(top)
        Label(top, text="1. SmartZone DPSK 관리", font=("Segoe UI", 14, "bold"),
              fg=ACCENT, bg=BG).pack(side=LEFT, padx=12)

        self.dpsk_ip = StringVar()
        self.dpsk_user = StringVar(value="admin")
        self.dpsk_pass = StringVar()
        self.dpsk_ctrl = StringVar(value="7.2.0" if "7.2.0" in CONTROLLER_API_MAP else "수동선택")
        self.dpsk_api = StringVar()
        self.dpsk_zone_filter = StringVar(value="전체 Zone")
        self.dpsk_search = StringVar()
        self.dpsk_create_zone = StringVar(value="선택")
        self.dpsk_create_wlan = StringVar()
        self.dpsk_create_user = StringVar()
        self.dpsk_create_count = StringVar(value="1")
        self.dpsk_create_psk = StringVar()
        self.dpsk_create_role = StringVar(value="선택 안 함")
        self.dpsk_create_vlan = StringVar()
        self.dpsk_create_group = StringVar(value="False (개인)")
        self._dpsk_api_cli = None
        self._dpsk_zones = []
        self._dpsk_all = []
        self._dpsk_wlans = []
        self._dpsk_roles = []

        body = Frame(outer, bg=BG)
        body.pack(fill=BOTH, expand=True, pady=(8, 0))

        side_wrap = Frame(body, bg=BG, width=268)
        side_wrap.pack(side=LEFT, fill=Y, padx=(0, 10))
        side_wrap.pack_propagate(False)
        side_canvas = Canvas(side_wrap, bg=BG, highlightthickness=0, width=248)
        side_sb = Scrollbar(side_wrap, orient=VERTICAL, command=side_canvas.yview)
        side_canvas.configure(yscrollcommand=side_sb.set)
        side_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        side_sb.pack(side=RIGHT, fill=Y)
        side = Frame(side_canvas, bg=BG)
        side_win = side_canvas.create_window((0, 0), window=side, anchor="nw")

        def _dpsk_side_scroll(_event=None):
            side_canvas.configure(scrollregion=side_canvas.bbox("all"))
            side_canvas.itemconfigure(side_win, width=side_canvas.winfo_width())

        side.bind("<Configure>", _dpsk_side_scroll)
        side_canvas.bind("<Configure>", _dpsk_side_scroll)

        def _dpsk_mousewheel(event):
            delta = -1 if getattr(event, "delta", 0) > 0 else 1
            if getattr(event, "num", None) == 4:
                delta = -1
            elif getattr(event, "num", None) == 5:
                delta = 1
            side_canvas.yview_scroll(delta, "units")

        side_canvas.bind("<Enter>", lambda e: side_canvas.bind_all("<MouseWheel>", _dpsk_mousewheel))
        side_canvas.bind("<Leave>", lambda e: side_canvas.unbind_all("<MouseWheel>"))
        side.bind("<Enter>", lambda e: side.bind_all("<MouseWheel>", _dpsk_mousewheel))
        side.bind("<Leave>", lambda e: side.unbind_all("<MouseWheel>"))

        def stack_label(parent, text):
            Label(parent, text=text, bg=CARD, font=("Segoe UI", 8), fg="#555").pack(anchor="w", pady=(6, 0))

        box1 = LabelFrame(side, text="1. 접속 설정", bg=CARD, fg="#333", font=("Segoe UI", 9, "bold"),
                          padx=8, pady=6)
        box1.pack(fill=X)
        stack_label(box1, "SZ IP/Domain")
        Entry(box1, textvariable=self.dpsk_ip, font=("Segoe UI", 10)).pack(fill=X)
        stack_label(box1, "Username")
        Entry(box1, textvariable=self.dpsk_user, font=("Segoe UI", 10)).pack(fill=X)
        stack_label(box1, "Password")
        Entry(box1, textvariable=self.dpsk_pass, show="*", font=("Segoe UI", 10)).pack(fill=X)
        stack_label(box1, "컨트롤러 버전")
        cb = ttk.Combobox(box1, textvariable=self.dpsk_ctrl, values=list(CONTROLLER_API_MAP.keys()),
                          state="readonly", width=26)
        cb.pack(fill=X)
        cb.bind("<<ComboboxSelected>>", lambda e: self._dpsk_update_api())
        stack_label(box1, "API 버전")
        self.dpsk_api_combo = ttk.Combobox(box1, textvariable=self.dpsk_api, state="readonly", width=26)
        self.dpsk_api_combo.pack(fill=X)
        Button(box1, text="로그인 & DPSK 조회", font=("Segoe UI", 9, "bold"), bg=LINK, fg="white",
               relief="flat", pady=5, command=self._dpsk_refresh, cursor="hand2").pack(fill=X, pady=(10, 4))
        self._dpsk_update_api()

        box2 = LabelFrame(side, text="2. DPSK 생성", bg=CARD, fg="#333", font=("Segoe UI", 9, "bold"),
                          padx=8, pady=6)
        box2.pack(fill=X, pady=(10, 0))
        stack_label(box2, "Zone")
        self.dpsk_cz_combo = ttk.Combobox(box2, textvariable=self.dpsk_create_zone, state="readonly")
        self.dpsk_cz_combo.pack(fill=X)
        self.dpsk_cz_combo.bind("<<ComboboxSelected>>", lambda e: self._dpsk_load_create_wlans())
        stack_label(box2, "WLAN 선택 (DPSK Enabled)")
        self.dpsk_cw_combo = ttk.Combobox(box2, textvariable=self.dpsk_create_wlan, state="readonly")
        self.dpsk_cw_combo.pack(fill=X)
        stack_label(box2, "Number of DPSKs")
        Entry(box2, textvariable=self.dpsk_create_count, font=("Segoe UI", 10)).pack(fill=X)
        stack_label(box2, "User Name")
        Entry(box2, textvariable=self.dpsk_create_user, font=("Segoe UI", 10)).pack(fill=X)
        stack_label(box2, "Passphrase (비우면 자동생성)")
        Entry(box2, textvariable=self.dpsk_create_psk, font=("Segoe UI", 10)).pack(fill=X)
        stack_label(box2, "User Role")
        self.dpsk_role_combo = ttk.Combobox(box2, textvariable=self.dpsk_create_role, state="readonly")
        self.dpsk_role_combo.pack(fill=X)
        stack_label(box2, "VLAN ID (1 – 4094, 선택 사항)")
        Entry(box2, textvariable=self.dpsk_create_vlan, font=("Segoe UI", 10)).pack(fill=X)
        stack_label(box2, "Group DPSK")
        ttk.Combobox(box2, textvariable=self.dpsk_create_group,
                     values=["False (개인)", "True (그룹)"], state="readonly").pack(fill=X)
        Button(box2, text="DPSK 생성하기", font=("Segoe UI", 9, "bold"), bg="#28a745", fg="white",
               relief="flat", pady=5, command=self._dpsk_create, cursor="hand2").pack(fill=X, pady=(10, 4))

        main = Frame(body, bg=CARD, padx=10, pady=8, highlightbackground="#dee2e6", highlightthickness=1)
        main.pack(side=LEFT, fill=BOTH, expand=True)
        filt = Frame(main, bg=CARD)
        filt.pack(fill=X)
        Label(filt, text="Zone 필터:", bg=CARD).pack(side=LEFT)
        self.dpsk_zone_combo = ttk.Combobox(filt, textvariable=self.dpsk_zone_filter, state="readonly", width=28)
        self.dpsk_zone_combo.pack(side=LEFT, padx=4)
        self.dpsk_zone_combo.bind("<<ComboboxSelected>>", lambda e: self._dpsk_fill_tree())
        Label(filt, text="검색:", bg=CARD).pack(side=LEFT, padx=(12, 0))
        Entry(filt, textvariable=self.dpsk_search, width=28).pack(side=LEFT, padx=4)
        Button(filt, text="검색", bg=LINK, fg="white", relief="flat", padx=10,
               command=self._dpsk_fill_tree).pack(side=LEFT)

        head = Frame(main, bg=CARD)
        head.pack(fill=X, pady=(8, 2))
        Label(head, text="DPSK 목록", font=("Segoe UI", 10, "bold"), bg=CARD, fg=LINK).pack(side=LEFT)
        self.dpsk_count = StringVar(value="총 0개")
        Label(head, textvariable=self.dpsk_count, bg=CARD, fg="#555").pack(side=RIGHT)
        Button(head, text="CSV 다운로드", bg="#28a745", fg="white", relief="flat", padx=8,
               command=self._dpsk_csv).pack(side=RIGHT, padx=4)
        Button(head, text="선택 항목 삭제", bg="#dc3545", fg="white", relief="flat", padx=8,
               command=self._dpsk_delete).pack(side=RIGHT, padx=4)
        Button(head, text="결과 폴더 열기", bg=BTN_BG, relief="solid", borderwidth=1, padx=8,
               command=lambda: self._open_path(RESULTS_DPSK)).pack(side=RIGHT, padx=4)
        Button(head, text="최근 결과 다운로드", bg="#28a745", fg="white", relief="flat", padx=8,
               command=lambda: self._download_latest_results(RESULTS_DPSK)).pack(side=RIGHT, padx=4)

        cols = ("zone", "wlan", "user", "psk", "mac", "role", "vlan", "group", "created", "exp", "status")
        tree_fr = Frame(main, bg=CARD)
        tree_fr.pack(fill=BOTH, expand=True)
        self.dpsk_tree = ttk.Treeview(tree_fr, columns=cols, show="headings", height=16, selectmode="extended")
        headers = {
            "zone": "Zone", "wlan": "WLAN 이름", "user": "User Name", "psk": "Passphrase",
            "mac": "MAC", "role": "User Role", "vlan": "VLAN", "group": "Group DPSK",
            "created": "생성일시", "exp": "만료일시", "status": "상태",
        }
        widths = {"zone": 90, "wlan": 110, "user": 90, "psk": 110, "mac": 110, "role": 80,
                  "vlan": 50, "group": 80, "created": 120, "exp": 120, "status": 70}
        for c in cols:
            self.dpsk_tree.heading(c, text=headers[c])
            self.dpsk_tree.column(c, width=widths[c], anchor="w")
        ysb = Scrollbar(tree_fr, command=self.dpsk_tree.yview)
        xsb = Scrollbar(tree_fr, orient=HORIZONTAL, command=self.dpsk_tree.xview)
        self.dpsk_tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.dpsk_tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        tree_fr.grid_rowconfigure(0, weight=1)
        tree_fr.grid_columnconfigure(0, weight=1)

        self.dpsk_status = StringVar(value="왼쪽에서 로그인 후 DPSK를 조회하세요.")
        Label(outer, textvariable=self.dpsk_status, font=("Segoe UI", 9), bg=BG, fg="#555").pack(anchor="w", pady=(6, 0))

    def _dpsk_update_api(self):
        vers = CONTROLLER_API_MAP.get(self.dpsk_ctrl.get(), CONTROLLER_API_MAP.get("수동선택", []))
        if hasattr(self, "dpsk_api_combo"):
            self.dpsk_api_combo["values"] = vers
        if vers and self.dpsk_api.get() not in vers:
            self.dpsk_api.set(vers[0])

    def _dpsk_fmt_time(self, raw):
        raw = raw or "-"
        if raw in ("-", ""):
            return "-", "-"
        if str(raw) == "Unlimited":
            return "무제한", "Active"
        if "from first use" in str(raw).lower():
            return "미사용", "Active"
        try:
            s = str(raw).replace("/", "-")
            dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                return str(raw), "-"
        # SZ 값은 UTC로 오는 경우가 많아 KST +9
        try:
            from datetime import timedelta
            local = dt + timedelta(hours=9)
        except Exception:
            local = dt
        status = "Expired" if local < datetime.now() else "Active"
        return local.strftime("%Y/%m/%d %H:%M:%S"), status

    def _dpsk_refresh(self):
        host = self.dpsk_ip.get().strip()
        user = self.dpsk_user.get().strip()
        pw = self.dpsk_pass.get()
        api = self.dpsk_api.get().strip()
        if not (host and user and pw and api):
            messagebox.showwarning("안내", "SZ IP / Username / Password / API 버전을 입력하세요.")
            return
        try:
            cli = SmartZoneAPI(host, user, pw, api)
            ok, msg = cli.login()
            if not ok:
                messagebox.showerror("로그인 실패", msg)
                return
            self._dpsk_api_cli = cli
            zones = cli.fetch_zones()
            self._dpsk_zones = zones
            labels = ["전체 Zone"]
            rows = []
            wlan_cache = {}
            for z in zones:
                zid = z.get("id") or ""
                zname = z.get("name") or zid
                labels.append(f"{zname}")
                dpsks = cli.fetch_dpsk_list(zid)
                for d in dpsks:
                    wid = d.get("wlanId") or ""
                    key = f"{zid}:{wid}"
                    if key not in wlan_cache and wid:
                        code, wd = cli.fetch_wlan(zid, wid)
                        wlan_cache[key] = (wd.get("name") if isinstance(wd, dict) else "") or ""
                    created, _ = self._dpsk_fmt_time(d.get("creationDateTime"))
                    exp, st = self._dpsk_fmt_time(d.get("expirationDateTime"))
                    if str(d.get("expirationDateTime")) == "Unlimited":
                        exp, st = "무제한", "Active"
                    rows.append({
                        "id": d.get("id") or "",
                        "zone_id": zid,
                        "zone": zname,
                        "wlan_id": wid,
                        "wlan": wlan_cache.get(key, ""),
                        "user": d.get("userName") or "",
                        "psk": d.get("passphrase") or "",
                        "mac": d.get("macAddress") or "Unbound",
                        "role": d.get("userRoleId") or "-",
                        "vlan": d.get("vlanId") if d.get("vlanId") not in (None, "") else "-",
                        "group": "True" if d.get("groupDpsk") else "False",
                        "created": created,
                        "exp": exp,
                        "status": st,
                    })
            self._dpsk_all = rows
            self.dpsk_zone_combo["values"] = labels
            if self.dpsk_zone_filter.get() not in labels:
                self.dpsk_zone_filter.set("전체 Zone")
            names = [z.get("name") or z.get("id") for z in zones]
            self.dpsk_cz_combo["values"] = names
            if names and self.dpsk_create_zone.get() in ("", "선택"):
                self.dpsk_create_zone.set(names[0])
                self._dpsk_load_create_wlans()
            try:
                roles = cli.fetch_user_roles()
            except Exception:
                roles = []
            self._dpsk_roles = roles
            role_labels = ["선택 안 함"] + [f"{r.get('name')}  [{(r.get('id') or '')[:8]}]" for r in roles]
            if hasattr(self, "dpsk_role_combo"):
                self.dpsk_role_combo["values"] = role_labels
            if self.dpsk_create_role.get() not in role_labels:
                self.dpsk_create_role.set("선택 안 함")
            self._dpsk_fill_tree()
            self.dpsk_status.set(f"{msg}  /  DPSK {len(rows)}건")
        except Exception as e:
            messagebox.showerror("오류", str(e))

    def _dpsk_fill_tree(self):
        tree = getattr(self, "dpsk_tree", None)
        if tree is None:
            return
        tree.delete(*tree.get_children())
        zf = self.dpsk_zone_filter.get()
        q = (self.dpsk_search.get() or "").strip().lower()
        n = 0
        for r in self._dpsk_all:
            if zf and zf not in ("ALL", "전체 Zone") and r.get("zone") != zf:
                continue
            blob = " ".join(str(r.get(k, "")) for k in ("zone", "wlan", "user", "psk", "mac", "role")).lower()
            if q and q not in blob:
                continue
            tree.insert("", END, iid=r["id"] or f"row{n}", values=(
                r["zone"], r["wlan"], r["user"], r["psk"], r["mac"], r.get("role", "-"),
                r["vlan"], r["group"], r["created"], r["exp"], r["status"],
            ))
            n += 1
        self.dpsk_count.set(f"총 {n}개")

    def _dpsk_zone_id(self, name):
        for z in self._dpsk_zones:
            if (z.get("name") or z.get("id")) == name or z.get("id") == name:
                return z.get("id")
        return ""

    def _dpsk_load_create_wlans(self):
        cli = self._dpsk_api_cli
        zid = self._dpsk_zone_id(self.dpsk_create_zone.get())
        if not cli or not zid:
            return
        try:
            wlans = cli.fetch_dpsk_wlans(zid)
            self._dpsk_wlans = wlans
            labels = [f"{w.get('name')}  ({w.get('ssid')})" for w in wlans]
            self.dpsk_cw_combo["values"] = labels
            if labels:
                self.dpsk_create_wlan.set(labels[0])
            else:
                self.dpsk_create_wlan.set("")
        except Exception as e:
            messagebox.showerror("WLAN 조회 실패", str(e))

    def _dpsk_create(self):
        cli = self._dpsk_api_cli
        zid = self._dpsk_zone_id(self.dpsk_create_zone.get())
        label = self.dpsk_create_wlan.get()
        username = self.dpsk_create_user.get().strip()
        if not cli or not zid:
            messagebox.showwarning("안내", "먼저 목록 조회를 하세요.")
            return
        wlan = None
        for w in self._dpsk_wlans:
            if f"{w.get('name')}  ({w.get('ssid')})" == label or w.get("id") == label:
                wlan = w
                break
        if not wlan:
            messagebox.showwarning("안내", "DPSK Enabled WLAN을 선택하세요.")
            return
        try:
            amount = int((self.dpsk_create_count.get() or "1").strip())
        except ValueError:
            messagebox.showwarning("안내", "Number of DPSKs 는 숫자여야 합니다.")
            return
        if amount < 1 or amount > 500:
            messagebox.showwarning("안내", "Number of DPSKs 범위는 1–500 입니다.")
            return
        if amount == 1 and username and any(r.get("zone_id") == zid and r.get("user") == username for r in self._dpsk_all):
            if not messagebox.askyesno("중복", f"사용자 '{username}' 이(가) 이미 있습니다. 강제 생성할까요?"):
                return
        vlan = None
        vs = self.dpsk_create_vlan.get().strip()
        if vs:
            try:
                vlan = int(vs)
            except ValueError:
                messagebox.showwarning("안내", "VLAN은 숫자여야 합니다.")
                return
        group = str(self.dpsk_create_group.get()).lower().startswith("true")
        role_id = ""
        role_label = self.dpsk_create_role.get()
        for rr in getattr(self, "_dpsk_roles", []):
            if f"{rr.get('name')}  [{rr.get('id')[:8]}]" == role_label or rr.get("name") == role_label:
                role_id = rr.get("id") or ""
                break
        passphrase = self.dpsk_create_psk.get().strip()
        code, body = cli.create_dpsk(
            zid, wlan["id"], username, group, vlan,
            amount=amount, passphrase=passphrase, user_role_id=role_id,
        )
        ok = code in (200, 201, 204)
        info = []
        if isinstance(body, dict):
            info = body.get("dpskInfoList") or []
            if body.get("error"):
                ok = False
        if ok:
            lines = []
            for it in info[:20]:
                if isinstance(it, dict):
                    lines.append(f"{it.get('userName','')}  /  {it.get('passphrase','')}")
            extra = "" if len(info) <= 20 else f"\n... 외 {len(info)-20}건"
            messagebox.showinfo("완료", f"{len(info) or amount}건 생성\n" + "\n".join(lines) + extra)
            self._dpsk_refresh()
        else:
            messagebox.showerror("생성 실패", str(body)[:500])

    def _dpsk_delete(self):
        cli = self._dpsk_api_cli
        if not cli:
            return
        sel = self.dpsk_tree.selection()
        if not sel:
            messagebox.showwarning("안내", "삭제할 DPSK를 선택하세요.")
            return
        if not messagebox.askyesno("확인", f"{len(sel)}건을 삭제할까요?"):
            return
        by = {}
        lookup = {r["id"]: r for r in self._dpsk_all}
        for iid in sel:
            r = lookup.get(iid)
            if not r:
                continue
            key = (r["zone_id"], r["wlan_id"])
            by.setdefault(key, []).append(r["id"])
        ok_n = fail_n = 0
        for (zid, wid), ids in by.items():
            code, body = cli.delete_dpsk(zid, wid, ids)
            if code in (200, 201, 204):
                ok_n += len(ids)
            else:
                fail_n += len(ids)
        messagebox.showinfo("삭제", f"성공 {ok_n} / 실패 {fail_n}")
        self._dpsk_refresh()

    def _dpsk_csv(self):
        rows = []
        zf = self.dpsk_zone_filter.get()
        q = (self.dpsk_search.get() or "").strip().lower()
        for r in self._dpsk_all:
            if zf and zf not in ("ALL", "전체 Zone") and r.get("zone") != zf:
                continue
            blob = " ".join(str(r.get(k, "")) for k in ("zone", "wlan", "user", "psk", "mac", "role")).lower()
            if q and q not in blob:
                continue
            rows.append(r)
        if not rows:
            messagebox.showwarning("안내", "저장할 목록이 없습니다.")
            return
        dest = filedialog.asksaveasfilename(
            title="DPSK CSV 저장",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"dpsk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not dest:
            return
        out = Path(dest)
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Zone", "WLAN 이름", "User Name", "Passphrase", "MAC", "User Role", "VLAN", "Group DPSK", "생성일시", "만료일시", "상태"])
            for r in rows:
                w.writerow([r["zone"], r["wlan"], r["user"], r["psk"], r["mac"], r.get("role", "-"), r["vlan"], r["group"],
                            r["created"], r["exp"], r["status"]])
        try:
            if RESULTS_DPSK.exists():
                for old in RESULTS_DPSK.glob("dpsk_*.csv"):
                    try:
                        old.unlink()
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            os.startfile(str(out.resolve()))
        except Exception:
            pass
        messagebox.showinfo("저장", f"{len(rows)}건 저장\n{out}")



    def _build_uldpsk(self):
        self._clear_page()
        outer = Frame(self, bg=BG, padx=12, pady=10)
        outer.pack(fill=BOTH, expand=True)
        top = Frame(outer, bg=BG)
        top.pack(fill=X)
        self._back_btn(top)
        Label(top, text="2. Unleashed DPSK 관리", font=("Segoe UI", 14, "bold"),
              fg=ACCENT, bg=BG).pack(side=LEFT, padx=12)

        self.udpsk_ip = StringVar()
        self.udpsk_user = StringVar(value="admin")
        self.udpsk_pass = StringVar()
        self.udpsk_search = StringVar()
        self.udpsk_wlan = StringVar()
        self.udpsk_user_name = StringVar()
        self.udpsk_count = StringVar(value="1")
        self.udpsk_vlan = StringVar()
        self._udpsk_cli = None
        self._udpsk_wlans = []
        self._udpsk_all = []

        body = Frame(outer, bg=BG)
        body.pack(fill=BOTH, expand=True, pady=(8, 0))
        side_wrap = Frame(body, bg=BG, width=268)
        side_wrap.pack(side=LEFT, fill=Y, padx=(0, 10))
        side_wrap.pack_propagate(False)
        side_canvas = Canvas(side_wrap, bg=BG, highlightthickness=0, width=248)
        side_sb = Scrollbar(side_wrap, orient=VERTICAL, command=side_canvas.yview)
        side_canvas.configure(yscrollcommand=side_sb.set)
        side_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        side_sb.pack(side=RIGHT, fill=Y)
        side = Frame(side_canvas, bg=BG)
        side_win = side_canvas.create_window((0, 0), window=side, anchor="nw")

        def _side_cfg(_e=None):
            side_canvas.configure(scrollregion=side_canvas.bbox("all"))
            side_canvas.itemconfigure(side_win, width=side_canvas.winfo_width())
        side.bind("<Configure>", _side_cfg)
        side_canvas.bind("<Configure>", _side_cfg)

        def _mw(event):
            delta = -1 if getattr(event, "delta", 0) > 0 else 1
            side_canvas.yview_scroll(delta, "units")
        side.bind("<Enter>", lambda e: side.bind_all("<MouseWheel>", _mw))
        side.bind("<Leave>", lambda e: side.unbind_all("<MouseWheel>"))

        def sl(parent, text):
            Label(parent, text=text, bg=CARD, font=("Segoe UI", 8), fg="#555").pack(anchor="w", pady=(6, 0))

        box1 = LabelFrame(side, text="1. 접속 설정", bg=CARD, fg="#333", font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        box1.pack(fill=X)
        sl(box1, "Unleashed IP/Domain")
        Entry(box1, textvariable=self.udpsk_ip, font=("Segoe UI", 10)).pack(fill=X)
        sl(box1, "Username")
        Entry(box1, textvariable=self.udpsk_user, font=("Segoe UI", 10)).pack(fill=X)
        sl(box1, "Password")
        Entry(box1, textvariable=self.udpsk_pass, show="*", font=("Segoe UI", 10)).pack(fill=X)
        Button(box1, text="로그인 & DPSK 조회", font=("Segoe UI", 9, "bold"), bg=LINK, fg="white",
               relief="flat", pady=5, command=self._udpsk_refresh, cursor="hand2").pack(fill=X, pady=(10, 4))

        box2 = LabelFrame(side, text="2. DPSK 생성", bg=CARD, fg="#333", font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        box2.pack(fill=X, pady=(10, 0))
        sl(box2, "WLAN 선택 (DPSK Enabled)")
        self.udpsk_wlan_combo = ttk.Combobox(box2, textvariable=self.udpsk_wlan, state="readonly")
        self.udpsk_wlan_combo.pack(fill=X)
        sl(box2, "Number of DPSKs")
        Entry(box2, textvariable=self.udpsk_count, font=("Segoe UI", 10)).pack(fill=X)
        sl(box2, "User Name")
        Entry(box2, textvariable=self.udpsk_user_name, font=("Segoe UI", 10)).pack(fill=X)
        sl(box2, "VLAN ID (선택)")
        Entry(box2, textvariable=self.udpsk_vlan, font=("Segoe UI", 10)).pack(fill=X)
        Button(box2, text="DPSK 생성하기", font=("Segoe UI", 9, "bold"), bg="#28a745", fg="white",
               relief="flat", pady=5, command=self._udpsk_create, cursor="hand2").pack(fill=X, pady=(10, 4))

        main = Frame(body, bg=CARD, padx=10, pady=8, highlightbackground="#dee2e6", highlightthickness=1)
        main.pack(side=LEFT, fill=BOTH, expand=True)
        filt = Frame(main, bg=CARD)
        filt.pack(fill=X)
        Label(filt, text="검색:", bg=CARD).pack(side=LEFT)
        Entry(filt, textvariable=self.udpsk_search, width=28).pack(side=LEFT, padx=4)
        Button(filt, text="검색", bg=LINK, fg="white", relief="flat", padx=10,
               command=self._udpsk_fill).pack(side=LEFT)
        head = Frame(main, bg=CARD)
        head.pack(fill=X, pady=(8, 2))
        Label(head, text="DPSK 목록", font=("Segoe UI", 10, "bold"), bg=CARD, fg=LINK).pack(side=LEFT)
        self.udpsk_count_lbl = StringVar(value="총 0개")
        Label(head, textvariable=self.udpsk_count_lbl, bg=CARD, fg="#555").pack(side=RIGHT)
        Button(head, text="CSV 다운로드", bg="#28a745", fg="white", relief="flat", padx=8,
               command=self._udpsk_csv).pack(side=RIGHT, padx=4)
        Button(head, text="선택 항목 삭제", bg="#dc3545", fg="white", relief="flat", padx=8,
               command=self._udpsk_delete).pack(side=RIGHT, padx=4)
        Button(head, text="결과 폴더 열기", bg=BTN_BG, relief="solid", borderwidth=1, padx=8,
               command=lambda: self._open_path(RESULTS_UDPSK)).pack(side=RIGHT, padx=4)
        Button(head, text="최근 결과 다운로드", bg="#28a745", fg="white", relief="flat", padx=8,
               command=lambda: self._download_latest_results(RESULTS_UDPSK)).pack(side=RIGHT, padx=4)

        cols = ("wlan", "dpsk_len", "shared_dpsk", "shared_num", "user", "psk", "vlan",
                "clients", "usage", "mac", "period", "status", "start_point",
                "limit_dpsk", "limit_num", "created", "expires")
        tree_fr = Frame(main, bg=CARD)
        tree_fr.pack(fill=BOTH, expand=True)
        self.udpsk_tree = ttk.Treeview(tree_fr, columns=cols, show="headings", height=16, selectmode="extended")
        headers = {
            "wlan": "WLAN 이름", "dpsk_len": "DPSK 길이", "shared_dpsk": "공유 DPSK",
            "shared_num": "공유 수", "user": "User Name", "psk": "Passphrase", "vlan": "VLAN",
            "clients": "사용 단말수", "usage": "Usage", "mac": "MAC 주소",
            "period": "사용가능기간", "status": "상태", "start_point": "시작 방식",
            "limit_dpsk": "DPSK 제한", "limit_num": "제한 수", "created": "생성일시", "expires": "만료일시",
        }
        widths = {
            "wlan": 150, "dpsk_len": 70, "shared_dpsk": 70, "shared_num": 50,
            "user": 120, "psk": 100, "vlan": 50, "clients": 70, "usage": 50,
            "mac": 120, "period": 80, "status": 90, "start_point": 70,
            "limit_dpsk": 70, "limit_num": 50, "created": 130, "expires": 130,
        }
        for c in cols:
            self.udpsk_tree.heading(c, text=headers[c])
            self.udpsk_tree.column(c, width=widths[c], anchor="w")
        self.udpsk_tree.tag_configure("active", foreground="#198754")
        self.udpsk_tree.tag_configure("expired", foreground="#dc3545")
        ysb = Scrollbar(tree_fr, command=self.udpsk_tree.yview)
        xsb = Scrollbar(tree_fr, orient=HORIZONTAL, command=self.udpsk_tree.xview)
        self.udpsk_tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.udpsk_tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        tree_fr.grid_rowconfigure(0, weight=1)
        tree_fr.grid_columnconfigure(0, weight=1)
        self.udpsk_status = StringVar(value="Unleashed IP / 계정 입력 후 조회하세요.")
        Label(outer, textvariable=self.udpsk_status, font=("Segoe UI", 9), bg=BG, fg="#555").pack(anchor="w", pady=(6, 0))

    def _udpsk_refresh(self):
        host = self.udpsk_ip.get().strip()
        user = self.udpsk_user.get().strip()
        pw = self.udpsk_pass.get()
        if not (host and user and pw):
            messagebox.showwarning("안내", "Unleashed IP / Username / Password 를 입력하세요.")
            return
        try:
            cli = UnleashedAPI(host, user, pw)
            ok, msg = cli.login()
            if not ok:
                messagebox.showerror("로그인 실패", msg)
                return
            self._udpsk_cli = cli
            wlans = cli.fetch_dpsk_wlans()
            self._udpsk_wlans = wlans
            wmap = {w.get("id"): w for w in wlans}
            labels = [f"{w.get('name')}  ({w.get('ssid')})" for w in wlans]
            self.udpsk_wlan_combo["values"] = labels
            if labels and not self.udpsk_wlan.get():
                self.udpsk_wlan.set(labels[0])
            self._udpsk_all = cli.fetch_dpsk_list(wmap)
            self._udpsk_fill()
            self.udpsk_status.set(f"{msg}  /  DPSK {len(self._udpsk_all)}건 / WLAN {len(wlans)}개")
        except Exception as e:
            messagebox.showerror("오류", str(e))

    def _udpsk_fill(self):
        tree = getattr(self, "udpsk_tree", None)
        if tree is None:
            return
        tree.delete(*tree.get_children())
        q = (self.udpsk_search.get() or "").strip().lower()
        n = 0
        for r in self._udpsk_all:
            blob = " ".join(str(r.get(k, "")) for k in ("wlan", "user", "psk", "mac")).lower()
            if q and q not in blob:
                continue
            iid = r.get("id") or f"row{n}"
            tag = "expired" if "만료" == r.get("status") else "active"
            tree.insert("", END, iid=str(iid), tags=(tag,), values=(
                r.get("wlan"), r.get("dpsk_len"), r.get("shared_dpsk"), r.get("shared_num"),
                r.get("user"), r.get("psk"), r.get("vlan"), r.get("clients"), r.get("usage"),
                r.get("mac"), r.get("period"), r.get("status"), r.get("start_point"),
                r.get("limit_dpsk"), r.get("limit_num"), r.get("created"), r.get("expires"),
            ))
            n += 1
        self.udpsk_count_lbl.set(f"총 {n}개")

    def _udpsk_wlan_id(self):
        label = self.udpsk_wlan.get()
        for w in self._udpsk_wlans:
            if f"{w.get('name')}  ({w.get('ssid')})" == label or w.get("id") == label:
                return w.get("id")
        return ""

    def _udpsk_create(self):
        cli = self._udpsk_cli
        wid = self._udpsk_wlan_id()
        if not cli or not wid:
            messagebox.showwarning("안내", "먼저 조회 후 DPSK WLAN을 선택하세요.")
            return
        try:
            amount = int((self.udpsk_count.get() or "1").strip())
        except ValueError:
            messagebox.showwarning("안내", "개수는 숫자여야 합니다.")
            return
        username = self.udpsk_user_name.get().strip()
        if amount == 1 and username:
            if any(r.get("wlan_id") == wid and (r.get("user") or "").lower() == username.lower() for r in self._udpsk_all):
                if not messagebox.askyesno("중복", f"사용자 '{username}' 이 이미 있습니다. 강제 생성할까요?"):
                    return
        ok, text = cli.create_dpsk(wid, username, self.udpsk_vlan.get().strip(), amount)
        if ok:
            messagebox.showinfo("완료", f"{amount}건 생성 요청 완료")
            self._udpsk_refresh()
        else:
            messagebox.showerror("생성 실패", text[:400])

    def _udpsk_delete(self):
        cli = self._udpsk_cli
        if not cli:
            return
        sel = self.udpsk_tree.selection()
        if not sel:
            messagebox.showwarning("안내", "삭제할 항목을 선택하세요.")
            return
        if not messagebox.askyesno("확인", f"{len(sel)}건을 삭제할까요?"):
            return
        ok, text = cli.delete_dpsk(list(sel))
        if ok:
            messagebox.showinfo("삭제", f"{len(sel)}건 삭제 요청 완료")
            self._udpsk_refresh()
        else:
            messagebox.showerror("삭제 실패", text[:400])

    def _udpsk_csv(self):
        q = (self.udpsk_search.get() or "").strip().lower()
        rows = []
        for r in self._udpsk_all:
            blob = " ".join(str(r.get(k, "")) for k in ("wlan", "user", "psk", "mac")).lower()
            if q and q not in blob:
                continue
            rows.append(r)
        if not rows:
            messagebox.showwarning("안내", "저장할 목록이 없습니다.")
            return
        dest = filedialog.asksaveasfilename(
            title="Unleashed DPSK CSV 저장",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"udpsk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        if not dest:
            return
        out = Path(dest)
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["WLAN 이름", "DPSK 길이", "공유 DPSK", "공유 수", "User Name", "Passphrase",
                        "VLAN", "사용 단말수", "Usage", "MAC 주소", "사용가능기간", "상태",
                        "시작 방식", "DPSK 제한", "제한 수", "생성일시", "만료일시"])
            for r in rows:
                w.writerow([
                    r.get("wlan"), r.get("dpsk_len"), r.get("shared_dpsk"), r.get("shared_num"),
                    r.get("user"), r.get("psk"), r.get("vlan"), r.get("clients"), r.get("usage"),
                    r.get("mac"), r.get("period"), r.get("status"), r.get("start_point"),
                    r.get("limit_dpsk"), r.get("limit_num"), r.get("created"), r.get("expires"),
                ])
        try:
            if RESULTS_UDPSK.exists():
                for old in RESULTS_UDPSK.glob("udpsk_*.csv"):
                    old.unlink()
        except Exception:
            pass
        try:
            os.startfile(str(out.resolve()))
        except Exception:
            pass
        messagebox.showinfo("저장", f"{len(rows)}건 저장\n{out}")


    def _download_latest_results(self, folder: Path, suffixes=None):
        folder = Path(folder)
        if not folder.is_dir():
            messagebox.showwarning("안내", "결과 폴더가 없습니다. 먼저 조회하세요.")
            return
        cands = [f for f in folder.iterdir() if f.is_file()]
        if suffixes:
            cands = [f for f in cands if any(f.name.endswith(s) for s in suffixes)]
        if not cands:
            messagebox.showwarning("안내", "다운로드할 결과 파일이 없습니다.")
            return
        src = max(cands, key=lambda p: p.stat().st_mtime)
        dest = filedialog.asksaveasfilename(
            title="최근 결과 저장",
            initialfile=src.name,
            defaultextension=src.suffix or ".csv",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
        )
        if not dest:
            return
        try:
            shutil.copy2(src, dest)
            messagebox.showinfo("다운로드", f"최근 결과 저장:\n{dest}")
        except Exception as e:
            messagebox.showerror("다운로드 실패", str(e))

    def _open_path(self, path: Path):
        path = Path(path)
        if path.exists() and path.is_file():
            target = path
        else:
            folder = path if path.suffix == "" else path.parent
            folder.mkdir(parents=True, exist_ok=True)
            target = folder
        try:
            os.startfile(str(target.resolve()))
        except Exception:
            messagebox.showinfo("경로", str(target.resolve()))


def main():
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        try:
            messagebox.showerror("실행 오류", f"{type(e).__name__}: {e}")
        except Exception:
            print(f"{type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
