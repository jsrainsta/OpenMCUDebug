"""参数面板（Stage 5 / v0.5）。

分组参数树 + 底部编辑下发区：

- 树：按 group 分组（无分组归入"默认"），列为 参数 / 当前值 / 范围 / 状态
- 选中参数后可在底部输入新值并下发（发出 set_requested 信号，由主窗口负责串口发送）
- 回执（$PA）以 ✓/✗ 着色显示在状态列
- 预设：current_values() 导出全部当前值；apply_preset() 显示载入值
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.param.param_manager import Param

DEFAULT_GROUP = "默认"

TREE_STYLE = (
    "QTreeWidget { background-color: #1e1f22; color: #c8c8c8;"
    " font-family: Consolas, 'Courier New'; font-size: 12px;"
    " alternate-background-color: #232428; }"
    "QHeaderView::section { background-color: #2b2d30; color: #a0a0a0;"
    " border: none; padding: 3px 6px; }"
)
HINT_STYLE = "QLabel { color: #a0a0a0; font-size: 12px; }"
OK_COLOR = QColor("#3dce7a")
ERR_COLOR = QColor("#e55d5d")


class ParamPanel(QWidget):
    """参数面板：展示 + 编辑，不直接接触串口（通过 set_requested 通知主窗口）。"""

    set_requested = pyqtSignal(int, str)   # (param_id, value_str)
    save_preset_requested = pyqtSignal(dict)   # {name: value_str}
    load_preset_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._items = {}    # param_id -> QTreeWidgetItem
        self._groups = {}   # group -> top-level QTreeWidgetItem
        self._params = {}   # param_id -> Param
        self._selected_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # -- 预设工具行 --
        tools = QHBoxLayout()
        tools.addWidget(QLabel("预设:"))
        self._save_preset_btn = QPushButton("保存预设…")
        self._save_preset_btn.clicked.connect(self._on_save_preset)
        tools.addWidget(self._save_preset_btn)
        self._load_preset_btn = QPushButton("载入预设…")
        self._load_preset_btn.clicked.connect(self._on_load_preset)
        tools.addWidget(self._load_preset_btn)
        tools.addStretch(1)
        self._ack_label = QLabel("")
        self._ack_label.setStyleSheet(HINT_STYLE)
        tools.addWidget(self._ack_label)
        layout.addLayout(tools)

        # -- 参数树 --
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["参数", "当前值", "范围", "状态"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setStyleSheet(TREE_STYLE)
        header = self._tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self._tree, stretch=1)

        # -- 编辑下发区 --
        edit_row = QHBoxLayout()
        self._detail_label = QLabel("未选择参数")
        self._detail_label.setStyleSheet(HINT_STYLE)
        edit_row.addWidget(self._detail_label, stretch=1)
        edit_row.addWidget(QLabel("新值:"))
        self._value_edit = QLineEdit()
        self._value_edit.setMaximumWidth(140)
        self._value_edit.returnPressed.connect(self._request_set)
        edit_row.addWidget(self._value_edit)
        self._set_btn = QPushButton("下发")
        self._set_btn.setEnabled(False)
        self._set_btn.clicked.connect(self._request_set)
        edit_row.addWidget(self._set_btn)
        layout.addLayout(edit_row)

    # ====== 对外接口 ======

    def add_param(self, param):
        """参数注册 → 加入（或更新）分组树。"""
        self._params[param.id] = param
        item = self._items.get(param.id)
        if item is None:
            group_item = self._group_item(param.group)
            item = QTreeWidgetItem([
                param.name,
                "" if param.value is None else str(param.value),
                self._range_text(param),
                "",
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, param.id)
            group_item.addChild(item)
            self._items[param.id] = item
        else:
            item.setText(0, param.name)
            item.setText(1, "" if param.value is None else str(param.value))
            item.setText(2, self._range_text(param))
        self._tree.expandAll()

    def update_value(self, param_id, raw_str, parsed_value):
        """参数值更新（$PV 或注册携带 val）→ 刷新树当前值列。"""
        item = self._items.get(param_id)
        if item is not None:
            item.setText(1, raw_str)
        if self._selected_id == param_id:
            # 若用户尚未编辑输入框，同步显示最新值
            if not self._value_edit.text():
                self._value_edit.setText(raw_str)

    def set_ack(self, param_id, ok, msg):
        """下发回执（$PA）→ 状态列着色显示。"""
        item = self._items.get(param_id)
        if item is None:
            return
        if ok:
            item.setText(3, "✓ 已应用")
            item.setForeground(3, QBrush(OK_COLOR))
        else:
            item.setText(3, "✗ " + (msg or "rejected"))
            item.setForeground(3, QBrush(ERR_COLOR))
        if self._selected_id == param_id:
            self._ack_label.setText(
                "✓ 已应用" if ok else ("✗ " + (msg or "rejected")))

    def reset(self):
        """清空全部参数。"""
        self._tree.clear()
        self._items.clear()
        self._groups.clear()
        self._params.clear()
        self._selected_id = None
        self._detail_label.setText("未选择参数")
        self._value_edit.clear()
        self._set_btn.setEnabled(False)
        self._ack_label.setText("")

    def current_values(self):
        """导出 {参数名: 当前值字符串}（预设保存用）。"""
        return {p.name: ("" if p.value is None else str(p.value))
                for p in self._params.values()}

    def apply_preset(self, values):
        """载入预设：按名称匹配参数并刷新当前值列（不自动下发）。"""
        by_name = {p.name: p for p in self._params.values()}
        applied = 0
        for name, value in values.items():
            param = by_name.get(name)
            if param is None:
                continue
            item = self._items.get(param.id)
            if item is not None:
                item.setText(1, value)
                item.setText(3, "预设")
            applied += 1
        return applied

    # ====== 内部 ======

    def _group_item(self, group):
        group = group or DEFAULT_GROUP
        item = self._groups.get(group)
        if item is None:
            item = QTreeWidgetItem([group])
            item.setData(0, Qt.ItemDataRole.UserRole, None)
            self._tree.addTopLevelItem(item)
            self._groups[group] = item
        return item

    @staticmethod
    def _range_text(param):
        if param.minimum is None and param.maximum is None:
            return ""
        lo = "-∞" if param.minimum is None else ("%.6g" % param.minimum)
        hi = "+∞" if param.maximum is None else ("%.6g" % param.maximum)
        return "%s ~ %s" % (lo, hi)

    def _on_selection_changed(self):
        item = self._tree.currentItem()
        if item is None or item.parent() is None:
            # 选中的是分组（顶层）或空 → 禁用下发
            self._selected_id = None
            self._detail_label.setText("未选择参数")
            self._value_edit.clear()
            self._set_btn.setEnabled(False)
            return
        param_id = item.data(0, Qt.ItemDataRole.UserRole)
        param = self._params.get(param_id)
        if param is None:
            return
        self._selected_id = param_id
        self._detail_label.setText(
            "%s  (%s)  [%s]" % (param.name, param.type,
                                param.group or DEFAULT_GROUP))
        self._value_edit.setText("" if param.value is None else str(param.value))
        self._set_btn.setEnabled(True)
        self._ack_label.setText("")

    def _request_set(self):
        if self._selected_id is None:
            return
        value = self._value_edit.text().strip()
        if not value:
            return
        self.set_requested.emit(self._selected_id, value)

    def _on_save_preset(self):
        values = self.current_values()
        if not values:
            return
        self.save_preset_requested.emit(values)

    def _on_load_preset(self):
        self.load_preset_requested.emit()
