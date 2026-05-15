from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QDateTime, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImageReader, QMovie, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from renew_curve.models import ReportStats
from renew_curve.scheduler import generated_review_times, validate_manual_review_times


def responsive_window_size(
    *,
    available_width: int,
    available_height: int,
    preferred_width: int,
    preferred_height: int,
    minimum_width: int,
    minimum_height: int,
) -> tuple[int, int, int, int]:
    usable_width = max(320, int(available_width * 0.92))
    usable_height = max(300, int(available_height * 0.88))
    min_width = min(minimum_width, usable_width)
    min_height = min(minimum_height, usable_height)
    width = min(preferred_width, max(min_width, usable_width))
    height = min(preferred_height, max(min_height, usable_height))
    return width, height, min_width, min_height


def screen_for_window(window) -> object | None:
    handle = window.windowHandle()
    if handle is not None and handle.screen() is not None:
        return handle.screen()
    parent = window.parentWidget()
    if parent is not None:
        parent_handle = parent.windowHandle()
        if parent_handle is not None and parent_handle.screen() is not None:
            return parent_handle.screen()
        parent_screen = parent.screen()
        if parent_screen is not None:
            return parent_screen
    current_screen = window.screen()
    if current_screen is not None:
        return current_screen
    return QApplication.primaryScreen()


def scaled_media_size(path: str | Path, max_size: int) -> QSize:
    source_size = QImageReader(str(path)).size()
    if not source_size.isValid() or source_size.width() <= 0 or source_size.height() <= 0:
        return QSize(max_size, max_size)
    width = source_size.width()
    height = source_size.height()
    if width >= height:
        return QSize(max_size, max(1, round(height * max_size / width)))
    return QSize(max(1, round(width * max_size / height)), max_size)


def fit_window_to_screen(
    window,
    *,
    preferred_width: int,
    preferred_height: int,
    minimum_width: int,
    minimum_height: int,
    constrain_to_screen: bool = True,
) -> None:
    screen = screen_for_window(window)
    if screen is None:
        if constrain_to_screen:
            window.setMaximumSize(preferred_width, preferred_height)
        else:
            window.setMaximumSize(16777215, 16777215)
        window.setMinimumSize(minimum_width, minimum_height)
        window.resize(preferred_width, preferred_height)
        return
    available = screen.availableGeometry()
    width, height, min_width, min_height = responsive_window_size(
        available_width=available.width(),
        available_height=available.height(),
        preferred_width=preferred_width,
        preferred_height=preferred_height,
        minimum_width=minimum_width,
        minimum_height=minimum_height,
    )
    if constrain_to_screen:
        window.setMaximumSize(available.width(), available.height())
    else:
        window.setMaximumSize(16777215, 16777215)
    window.setMinimumSize(min_width, min_height)
    window.resize(width, height)
    window.move(
        available.x() + max(0, (available.width() - width) // 2),
        available.y() + max(0, (available.height() - height) // 2),
    )


class PersonalizationPreviewPanel(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PersonalizationPreview")
        self.background_path: str | None = None
        self.sticker_path: str | None = None
        self.overlay_alpha = 153
        self.blur_radius = 0
        self.darken_alpha = 0
        self._sticker_movie: QMovie | None = None
        self._sticker_label = QLabel(self)
        self._sticker_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )
        self._sticker_label.hide()

    def set_preview(
        self,
        *,
        background_path: str | None,
        sticker_path: str | None,
        overlay_alpha: int,
        blur_radius: int,
        darken_alpha: int,
    ) -> None:
        self.background_path = background_path
        self.sticker_path = sticker_path
        self.overlay_alpha = max(0, min(255, overlay_alpha))
        self.blur_radius = max(0, min(30, blur_radius))
        self.darken_alpha = max(0, min(255, darken_alpha))
        self._sync_sticker_movie()
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_sticker_label()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 8, 8)
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), QColor(255, 255, 255, 238))

        if self.background_path:
            background = QPixmap(self.background_path)
            if not background.isNull():
                scaled = background.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                scaled = self._blurred_pixmap(scaled, self.blur_radius)
                painter.drawPixmap(
                    (self.width() - scaled.width()) // 2,
                    (self.height() - scaled.height()) // 2,
                    scaled,
                )
                if self.darken_alpha:
                    painter.fillRect(self.rect(), QColor(0, 0, 0, self.darken_alpha))
                painter.fillRect(self.rect(), QColor(255, 255, 255, self.overlay_alpha))

        if self.sticker_path and not self._is_gif_sticker():
            sticker = QPixmap(self.sticker_path)
            if not sticker.isNull():
                scaled = sticker.scaled(
                    88,
                    88,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(
                    self.width() - scaled.width() - 18,
                    self.height() - scaled.height() - 18,
                    scaled,
                )

        painter.setClipping(False)
        painter.setPen(QColor("#d9e2ef"))
        painter.drawRoundedRect(rect, 8, 8)

    def _is_gif_sticker(self) -> bool:
        return bool(self.sticker_path and Path(self.sticker_path).suffix.lower() == ".gif")

    def _sync_sticker_movie(self) -> None:
        if self._sticker_movie is not None:
            self._sticker_movie.stop()
            self._sticker_movie.deleteLater()
            self._sticker_movie = None
        self._sticker_label.clear()
        self._sticker_label.hide()
        if not self._is_gif_sticker() or self.sticker_path is None:
            return
        movie = QMovie(self.sticker_path, parent=self._sticker_label)
        if not movie.isValid():
            return
        movie.setScaledSize(scaled_media_size(self.sticker_path, 88))
        self._sticker_movie = movie
        self._sticker_label.setMovie(movie)
        self._sticker_label.setFixedSize(movie.scaledSize())
        self._position_sticker_label()
        self._sticker_label.show()
        movie.start()

    def _position_sticker_label(self) -> None:
        if self._sticker_label.isHidden():
            return
        self._sticker_label.move(
            max(12, self.width() - self._sticker_label.width() - 18),
            max(12, self.height() - self._sticker_label.height() - 18),
        )
        self._sticker_label.raise_()

    @staticmethod
    def _blurred_pixmap(pixmap: QPixmap, radius: int) -> QPixmap:
        if radius <= 0 or pixmap.isNull():
            return pixmap
        scene = QGraphicsScene()
        item = QGraphicsPixmapItem(pixmap)
        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(radius)
        item.setGraphicsEffect(effect)
        scene.addItem(item)
        result = QPixmap(pixmap.size())
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        scene.render(painter, QRectF(result.rect()), QRectF(pixmap.rect()))
        painter.end()
        return result


class SettingsDialog(QDialog):
    _responsive_size = {
        "preferred_width": 1440,
        "preferred_height": 740,
        "minimum_width": 960,
        "minimum_height": 560,
    }

    def __init__(
        self,
        parent=None,
        current: dict[str, str] | None = None,
        upload_background: Callable[[Path], None] | None = None,
        upload_sticker: Callable[[Path], None] | None = None,
        delete_background: Callable[[int], None] | None = None,
        delete_sticker: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("個人化")
        fit_window_to_screen(self, **self._responsive_size)
        current = current or {}
        self._upload_background = upload_background
        self._upload_sticker = upload_sticker
        self._delete_background = delete_background
        self._delete_sticker = delete_sticker

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["light", "dark", "system"])
        self._set_current(self.theme_combo, current.get("theme", "light"))

        self.accent_combo = QComboBox()
        self.accent_combo.addItems(["blue", "green", "purple", "orange", "gray"])
        self._set_current(self.accent_combo, current.get("accent", "blue"))

        self.density_combo = QComboBox()
        self.density_combo.addItems(["comfortable", "compact"])
        self._set_current(self.density_combo, current.get("density", "comfortable"))

        self.snooze_combo = QComboBox()
        self.snooze_combo.addItems(["10m", "1h", "tomorrow"])
        self._set_current(self.snooze_combo, current.get("default_snooze", "10m"))

        self.theme_style_combo = QComboBox()
        self.theme_style_combo.addItems(["clean_mountain", "healing_pastel", "dark_focus"])
        self._set_current(
            self.theme_style_combo, current.get("theme_style", "clean_mountain")
        )

        self.sticker_scope_combo = QComboBox()
        self.sticker_scope_combo.addItems(["main_only", "all_windows", "disabled"])
        self._set_current(
            self.sticker_scope_combo, current.get("sticker_scope", "main_only")
        )

        self.functional_sticker_density_combo = QComboBox()
        self.functional_sticker_density_combo.addItems(["low", "normal", "high"])
        self._set_current(
            self.functional_sticker_density_combo,
            current.get("functional_window_sticker_density", "low"),
        )

        self.background_mode_combo = QComboBox()
        self.background_mode_combo.addItem("指定背景", "selected")
        self.background_mode_combo.addItem("隨機背景", "random")
        mode_index = self.background_mode_combo.findData(
            current.get("background_mode", "selected")
        )
        self.background_mode_combo.setCurrentIndex(mode_index if mode_index >= 0 else 0)
        self.background_mode_combo.currentIndexChanged.connect(
            lambda _index: self._sync_background_mode()
        )

        self.sticker_mode_combo = QComboBox()
        self.sticker_mode_combo.addItem("指定貼圖", "selected")
        self.sticker_mode_combo.addItem("隨機貼圖", "random")
        sticker_mode_index = self.sticker_mode_combo.findData(
            current.get("sticker_mode", "selected")
        )
        self.sticker_mode_combo.setCurrentIndex(
            sticker_mode_index if sticker_mode_index >= 0 else 0
        )
        self.sticker_mode_combo.currentIndexChanged.connect(
            lambda _index: self._sync_sticker_mode()
        )
        self.selected_sticker_combo = QComboBox()
        self.selected_sticker_combo.currentIndexChanged.connect(
            lambda _index: self._update_preview()
        )

        self.background_overlay_spin = QSpinBox()
        self.background_overlay_spin.setRange(0, 100)
        self.background_overlay_spin.setValue(int(current.get("background_overlay", "60")))
        self.background_overlay_spin.valueChanged.connect(
            lambda _value: self._update_preview()
        )

        self.background_blur_spin = QSpinBox()
        self.background_blur_spin.setRange(0, 30)
        self.background_blur_spin.setValue(int(current.get("background_blur", "0")))
        self.background_blur_spin.valueChanged.connect(
            lambda _value: self._update_preview()
        )

        self.background_darken_spin = QSpinBox()
        self.background_darken_spin.setRange(0, 100)
        self.background_darken_spin.setValue(int(current.get("background_darken", "20")))
        self.background_darken_spin.valueChanged.connect(
            lambda _value: self._update_preview()
        )

        self.background_assets: list[tuple[int, str, str, bool]] = []
        self.sticker_assets: list[tuple[int, str, str, bool]] = []
        self.background_delete_buttons: dict[int, QPushButton] = {}
        self.sticker_delete_buttons: dict[int, QPushButton] = {}
        self._background_selections = {
            "today_background_id": current.get("today_background_id", ""),
            "next_background_id": current.get("next_background_id", ""),
            "all_background_id": current.get("all_background_id", ""),
        }
        self._selected_sticker_id = current.get("selected_sticker_id", "")

        self.interface_section_title = QLabel("基本偏好")
        self.interface_section_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        self.interface_help_label = QLabel(
            "基本偏好會影響主畫面色彩、間距、推延預設與貼圖顯示。素材管理集中在下方。"
        )
        self.interface_help_label.setObjectName("Muted")
        self.interface_help_label.setWordWrap(True)
        self.interface_help_label.hide()
        self.accent_help_label = QLabel("重點色會套用在按鈕、選取狀態與月曆焦點。")
        self.accent_help_label.setObjectName("Muted")
        self.accent_help_label.setWordWrap(True)
        self.accent_help_label.hide()
        self.density_help_label = QLabel("密度會影響留白與列表高度，16 吋與 27 吋螢幕都會較好閱讀。")
        self.density_help_label.setObjectName("Muted")
        self.density_help_label.setWordWrap(True)
        self.density_help_label.hide()
        interface_form = QGridLayout()
        self.interface_form_layout = interface_form
        interface_form.setHorizontalSpacing(12)
        interface_form.setVerticalSpacing(8)
        interface_fields = [
            ("主題", self.theme_combo),
            ("重點色", self.accent_combo),
            ("密度", self.density_combo),
            ("推延", self.snooze_combo),
            ("主題模式", self.theme_style_combo),
            ("貼圖範圍", self.sticker_scope_combo),
            ("視窗貼圖密度", self.functional_sticker_density_combo),
        ]
        for index, (label_text, widget) in enumerate(interface_fields):
            row = index // 2
            column = (index % 2) * 2
            label = QLabel(label_text)
            label.setObjectName("Muted")
            interface_form.addWidget(label, row, column)
            widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            interface_form.addWidget(widget, row, column + 1)
        interface_form.setColumnStretch(1, 1)
        interface_form.setColumnStretch(3, 1)

        interface_panel = QFrame()
        self.interface_panel = interface_panel
        interface_panel.setObjectName("Panel")
        interface_panel.setMaximumHeight(220)
        interface_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        interface_layout = QVBoxLayout(interface_panel)
        interface_layout.addWidget(self.interface_section_title)
        interface_layout.addLayout(interface_form)

        self.background_assets_title = QLabel("背景庫")
        self.background_assets_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        self.background_assets_title.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        self.background_assets_title.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        background_panel = QFrame()
        background_panel.setObjectName("Panel")
        background_layout = QVBoxLayout(background_panel)
        self.background_panel_layout = background_layout
        background_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        background_layout.addWidget(self.background_assets_title)

        self.upload_background_button = QPushButton("上傳背景圖片")
        self.upload_background_button.clicked.connect(self._choose_and_upload_background)
        background_layout.addWidget(self.upload_background_button)

        sliders = QFormLayout()
        sliders.addRow("背景模式", self.background_mode_combo)
        sliders.addRow("背景透明遮罩", self.background_overlay_spin)
        sliders.addRow("背景模糊", self.background_blur_spin)
        sliders.addRow("背景暗化", self.background_darken_spin)
        background_layout.addLayout(sliders)

        self.today_background_combo = QComboBox()
        self.next_background_combo = QComboBox()
        self.all_background_combo = QComboBox()
        for combo in (
            self.today_background_combo,
            self.next_background_combo,
            self.all_background_combo,
        ):
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            combo.setMinimumContentsLength(16)
            combo.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
            )
            combo.currentIndexChanged.connect(lambda _index: self._update_preview())
        background_form = QFormLayout()
        background_form.addRow("今天任務背景", self.today_background_combo)
        background_form.addRow("接下來 3 天背景", self.next_background_combo)
        background_form.addRow("所有任務背景", self.all_background_combo)
        background_layout.addLayout(background_form)

        self.background_list = QVBoxLayout()
        background_list_widget = QWidget()
        background_list_layout = QVBoxLayout(background_list_widget)
        background_list_layout.setContentsMargins(0, 0, 0, 0)
        background_list_layout.addLayout(self.background_list)
        self.background_asset_scroll = QScrollArea()
        self.background_asset_scroll.setWidgetResizable(True)
        self.background_asset_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.background_asset_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.background_asset_scroll.setWidget(background_list_widget)
        self.background_asset_scroll.setMinimumHeight(220)
        self.background_asset_scroll.setMaximumHeight(320)
        background_layout.addWidget(self.background_asset_scroll, 1)
        self.asset_scroll = self.background_asset_scroll

        self.sticker_assets_title = QLabel("貼圖庫")
        self.sticker_assets_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        self.sticker_assets_title.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        self.sticker_assets_title.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        sticker_panel = QFrame()
        sticker_panel.setObjectName("Panel")
        sticker_layout = QVBoxLayout(sticker_panel)
        self.sticker_panel_layout = sticker_layout
        sticker_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        sticker_layout.addWidget(self.sticker_assets_title)
        self.upload_sticker_button = QPushButton("上傳貼圖 PNG / GIF")
        self.upload_sticker_button.clicked.connect(self._choose_and_upload_sticker)
        sticker_layout.addWidget(self.upload_sticker_button)
        sticker_form = QFormLayout()
        sticker_form.addRow("貼圖模式", self.sticker_mode_combo)
        sticker_form.addRow("指定貼圖", self.selected_sticker_combo)
        sticker_layout.addLayout(sticker_form)
        self.sticker_list = QVBoxLayout()
        sticker_list_widget = QWidget()
        sticker_list_layout = QVBoxLayout(sticker_list_widget)
        sticker_list_layout.setContentsMargins(0, 0, 0, 0)
        sticker_list_layout.addLayout(self.sticker_list)
        self.sticker_asset_scroll = QScrollArea()
        self.sticker_asset_scroll.setWidgetResizable(True)
        self.sticker_asset_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.sticker_asset_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.sticker_asset_scroll.setWidget(sticker_list_widget)
        self.sticker_asset_scroll.setMinimumHeight(220)
        self.sticker_asset_scroll.setMaximumHeight(320)
        sticker_layout.addWidget(self.sticker_asset_scroll, 1)

        self.background_panel = background_panel
        self.sticker_panel = sticker_panel
        asset_columns = QWidget()
        self.asset_columns_layout = QHBoxLayout(asset_columns)
        self.asset_columns_layout.setContentsMargins(0, 0, 0, 0)
        self.asset_columns_layout.setSpacing(14)
        self.asset_columns_layout.addWidget(self.background_panel, 1)
        self.asset_columns_layout.addWidget(self.sticker_panel, 1)

        left_content = QWidget()
        self.left_content = left_content
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)
        left_layout.addWidget(interface_panel)
        left_layout.addWidget(asset_columns, 1)

        self.preview_title = QLabel("預覽")
        self.preview_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        preview_container = QWidget()
        self.preview_container = preview_container
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(10)
        preview_layout.addWidget(self.preview_title)
        self.today_preview_panel = self._build_preview_panel("今天任務背景")
        self.next_preview_panel = self._build_preview_panel("接下來 3 天背景")
        self.all_preview_panel = self._build_preview_panel("所有任務背景")
        self.preview_panel = self.today_preview_panel
        preview_layout.addWidget(self.today_preview_panel)
        preview_layout.addWidget(self.next_preview_panel)
        preview_layout.addWidget(self.all_preview_panel)
        preview_layout.addStretch(1)

        header = QHBoxLayout()
        title = QLabel("個人化")
        title.setStyleSheet("font-size: 24px; font-weight: 800;")
        header.addWidget(title, 1)
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(36, 36)
        self.close_button.clicked.connect(self.reject)
        header.addWidget(self.close_button)

        body_container = QWidget()
        body = QHBoxLayout(body_container)
        self.body_layout = body
        body.setSpacing(16)
        body.addWidget(left_content, 3)
        body.addWidget(preview_container, 2)
        self.body_scroll = QScrollArea()
        self.body_scroll.setWidgetResizable(True)
        self.body_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.body_scroll.setWidget(body_container)

        self.apply_button = QPushButton("套用設定")
        self.apply_button.setObjectName("PrimaryButton")
        self.apply_button.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.apply_button)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.body_scroll, 1)
        layout.addLayout(footer)
        self._render_asset_lists()
        self._populate_background_selectors()
        self._populate_sticker_selector()
        self._sync_background_mode()
        self._sync_sticker_mode()
        self._update_preview()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        fit_window_to_screen(self, **self._responsive_size)

    def values(self) -> dict[str, str]:
        return {
            "theme": self.theme_combo.currentText(),
            "accent": self.accent_combo.currentText(),
            "density": self.density_combo.currentText(),
            "default_snooze": self.snooze_combo.currentText(),
            "theme_style": self.theme_style_combo.currentText(),
            "sticker_scope": self.sticker_scope_combo.currentText(),
            "functional_window_sticker_density": self.functional_sticker_density_combo.currentText(),
            "sticker_mode": str(self.sticker_mode_combo.currentData() or "selected"),
            "selected_sticker_id": str(self.selected_sticker_combo.currentData() or ""),
            "background_mode": str(self.background_mode_combo.currentData() or "selected"),
            "background_overlay": str(self.background_overlay_spin.value()),
            "background_blur": str(self.background_blur_spin.value()),
            "background_darken": str(self.background_darken_spin.value()),
            "today_background_id": str(self.today_background_combo.currentData() or ""),
            "next_background_id": str(self.next_background_combo.currentData() or ""),
            "all_background_id": str(self.all_background_combo.currentData() or ""),
        }

    def set_background_assets(self, assets: list[tuple[int, str, str, bool]]) -> None:
        self.background_assets = assets
        self._populate_background_selectors()
        self._render_asset_lists()
        self._update_preview()

    def set_sticker_assets(self, assets: list[tuple[int, str, str, bool]]) -> None:
        self.sticker_assets = assets
        self._populate_sticker_selector()
        self._render_asset_lists()
        self._sync_sticker_mode()
        self._update_preview()

    def choose_background_file(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "上傳背景圖片",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        return Path(path) if path else None

    def choose_sticker_file(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "上傳貼圖",
            "",
            "Images (*.png *.gif *.jpg *.jpeg *.webp *.bmp)",
        )
        return Path(path) if path else None

    def _choose_and_upload_background(self) -> None:
        path = self.choose_background_file()
        if path is not None and self._upload_background is not None:
            self._upload_background(path)

    def _choose_and_upload_sticker(self) -> None:
        path = self.choose_sticker_file()
        if path is not None and self._upload_sticker is not None:
            self._upload_sticker(path)

    def _render_asset_lists(self) -> None:
        if not hasattr(self, "background_list"):
            return
        self._fill_asset_list(
            self.background_list,
            self.background_assets,
            "尚未上傳背景",
            "background",
        )
        self._fill_asset_list(
            self.sticker_list,
            self.sticker_assets,
            "尚未上傳貼圖",
            "sticker",
        )

    def _fill_asset_list(
        self,
        layout: QVBoxLayout,
        assets: list[tuple[int, str, str, bool]],
        empty_text: str,
        kind: str,
    ) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        if not assets:
            empty = QLabel(empty_text)
            empty.setObjectName("Muted")
            layout.addWidget(empty)
            return
        if kind == "background":
            self.background_delete_buttons = {}
        else:
            self.sticker_delete_buttons = {}
        for asset_id, name, _path, active in assets:
            row = QFrame()
            row.setObjectName("AssetRow")
            row.setFixedHeight(64)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(8)
            thumbnail = QLabel("")
            thumbnail.setObjectName("AssetThumbnail")
            thumbnail.setFixedSize(48, 48)
            thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if Path(_path).suffix.lower() == ".gif":
                movie = QMovie(_path, parent=thumbnail)
                if movie.isValid():
                    movie.setScaledSize(scaled_media_size(_path, 48))
                    thumbnail.setMovie(movie)
                    movie.start()
                else:
                    thumbnail.setText("圖")
            else:
                pixmap = QPixmap(_path)
                if pixmap.isNull():
                    thumbnail.setText("圖")
                else:
                    thumbnail.setPixmap(
                        pixmap.scaled(
                            48,
                            48,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
            row_layout.addWidget(thumbnail)
            name_label = QLabel(name)
            name_label.setObjectName("AssetName")
            name_label.setToolTip(name)
            name_width = name_label.fontMetrics().horizontalAdvance(name) + 18
            name_label.setMinimumWidth(max(320, name_width))
            name_label.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
            )
            name_scroll = QScrollArea()
            name_scroll.setObjectName("AssetNameScroll")
            name_scroll.setWidgetResizable(False)
            name_scroll.setFrameShape(QFrame.Shape.NoFrame)
            name_scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            name_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            name_scroll.setFixedHeight(46)
            name_scroll.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            name_scroll.setWidget(name_label)
            row_layout.addWidget(name_scroll, 1)
            state = QLabel("使用中" if active else "未使用")
            state.setObjectName("Muted")
            row_layout.addWidget(state)
            delete_button = QPushButton("刪除")
            delete_button.setObjectName("AssetDeleteButton")
            if kind == "background":
                delete_button.clicked.connect(
                    lambda _checked=False, current_id=asset_id: self._request_delete_background(current_id)
                )
                self.background_delete_buttons[asset_id] = delete_button
            else:
                delete_button.clicked.connect(
                    lambda _checked=False, current_id=asset_id: self._request_delete_sticker(current_id)
                )
                self.sticker_delete_buttons[asset_id] = delete_button
            row_layout.addWidget(delete_button)
            layout.addWidget(row)

    def _request_delete_background(self, asset_id: int) -> None:
        if self._delete_background is not None:
            self._delete_background(asset_id)

    def _request_delete_sticker(self, asset_id: int) -> None:
        if self._delete_sticker is not None:
            self._delete_sticker(asset_id)

    def _build_preview_panel(self, title: str) -> PersonalizationPreviewPanel:
        panel = PersonalizationPreviewPanel()
        panel.setMinimumHeight(130)
        layout = QVBoxLayout(panel)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 800;")
        sample = QLabel("英文單字 Unit 12")
        sample.setObjectName("Muted")
        layout.addWidget(title_label)
        layout.addWidget(sample)
        layout.addStretch(1)
        return panel

    def _sync_background_mode(self) -> None:
        random_mode = self.background_mode_combo.currentData() == "random"
        for combo in (
            self.today_background_combo,
            self.next_background_combo,
            self.all_background_combo,
        ):
            combo.setEnabled(not random_mode)
        self._update_preview()

    def _populate_sticker_selector(self) -> None:
        selection = self.selected_sticker_combo.currentData() or self._selected_sticker_id
        self.selected_sticker_combo.blockSignals(True)
        self.selected_sticker_combo.clear()
        self.selected_sticker_combo.addItem("使用最新上傳貼圖", "")
        for asset_id, name, _path, active in self.sticker_assets:
            if active:
                self.selected_sticker_combo.addItem(name, str(asset_id))
        index = self.selected_sticker_combo.findData(str(selection))
        self.selected_sticker_combo.setCurrentIndex(index if index >= 0 else 0)
        self.selected_sticker_combo.blockSignals(False)

    def _sync_sticker_mode(self) -> None:
        random_mode = self.sticker_mode_combo.currentData() == "random"
        self.selected_sticker_combo.setEnabled(not random_mode)
        self._update_preview()

    def _populate_background_selectors(self) -> None:
        selections = {
            "today_background_id": self.today_background_combo.currentData()
            or self._background_selections["today_background_id"],
            "next_background_id": self.next_background_combo.currentData()
            or self._background_selections["next_background_id"],
            "all_background_id": self.all_background_combo.currentData()
            or self._background_selections["all_background_id"],
        }
        combos = {
            "today_background_id": self.today_background_combo,
            "next_background_id": self.next_background_combo,
            "all_background_id": self.all_background_combo,
        }
        for key, combo in combos.items():
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("使用最新上傳背景", "")
            for asset_id, name, _path, active in self.background_assets:
                if active:
                    combo.addItem(name, str(asset_id))
            index = combo.findData(str(selections[key]))
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

    def _selected_background_path(self, combo: QComboBox) -> str | None:
        selected_id = str(combo.currentData() or "")
        active_assets = [asset for asset in self.background_assets if asset[3]]
        if selected_id:
            for asset_id, _name, path, _active in active_assets:
                if str(asset_id) == selected_id:
                    return path
        return active_assets[0][2] if active_assets else None

    def _active_sticker_path(self) -> str | None:
        selected_id = str(self.selected_sticker_combo.currentData() or "")
        for _asset_id, _name, path, active in self.sticker_assets:
            if selected_id and str(_asset_id) == selected_id and active:
                return path
        for _asset_id, _name, path, active in self.sticker_assets:
            if active:
                return path
        return None

    def _update_preview(self) -> None:
        if not hasattr(self, "today_preview_panel"):
            return
        overlay_alpha = int(255 * self.background_overlay_spin.value() / 100)
        darken_alpha = int(255 * self.background_darken_spin.value() / 100)
        sticker_path = self._active_sticker_path()
        preview_pairs = (
            (self.today_preview_panel, self.today_background_combo),
            (self.next_preview_panel, self.next_background_combo),
            (self.all_preview_panel, self.all_background_combo),
        )
        for panel, combo in preview_pairs:
            panel.set_preview(
                background_path=self._selected_background_path(combo),
                sticker_path=sticker_path,
                overlay_alpha=overlay_alpha,
                blur_radius=self.background_blur_spin.value(),
                darken_alpha=darken_alpha,
            )

    @staticmethod
    def _set_current(combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)


class TaskDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新增任務")

        self.title_edit = QLineEdit()
        self.category_edit = QComboBox()
        self.category_edit.setEditable(True)
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["初級", "中級", "高級"])
        self.notes_edit = QTextEdit()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["遺忘曲線", "手動輸入"])
        self.schedule_help_label = QLabel(
            "遺忘曲線會依開始時間自動產生複習點；手動輸入可自行指定每一次提醒時間。"
        )
        self.schedule_help_label.setObjectName("Muted")
        self.schedule_help_label.setWordWrap(True)
        self.start_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.review_count_spin = QSpinBox()
        self.review_count_spin.setRange(3, 10)
        self.review_count_spin.setValue(5)
        self.manual_time_edits: list[QDateTimeEdit] = []
        self.manual_time_rows: list[QWidget] = []
        for _ in range(10):
            edit = QDateTimeEdit(QDateTime.currentDateTime())
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd HH:mm")
            self.manual_time_edits.append(edit)

        self.manual_times_widget = QWidget()
        self.manual_times_layout = QVBoxLayout(self.manual_times_widget)
        self.manual_times_layout.setContentsMargins(0, 0, 0, 0)
        self.manual_times_layout.setSpacing(8)
        for index, edit in enumerate(self.manual_time_edits, start=1):
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(QLabel(f"第 {index} 次"))
            row.addWidget(edit, 1)
            self.manual_time_rows.append(row_widget)
            self.manual_times_layout.addWidget(row_widget)

        form = QFormLayout()
        form.addRow("任務名稱", self.title_edit)
        form.addRow("分類", self.category_edit)
        form.addRow("難度", self.difficulty_combo)
        form.addRow("筆記", self.notes_edit)
        form.addRow("提醒模式", self.mode_combo)
        form.addRow("", self.schedule_help_label)
        form.addRow("開始時間", self.start_edit)
        form.addRow("複習次數", self.review_count_spin)

        left_panel = QFrame()
        left_panel.setObjectName("Panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.addLayout(form)
        left_layout.addWidget(self.manual_times_widget)

        self.preview_layout = QVBoxLayout()
        preview_panel = QFrame()
        preview_panel.setObjectName("Panel")
        preview_layout = QVBoxLayout(preview_panel)
        title = QLabel("複習日期預覽")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        hint = QLabel("新增前先確認會產生哪些提醒。")
        hint.setObjectName("Muted")
        preview_layout.addWidget(title)
        preview_layout.addWidget(hint)
        preview_layout.addLayout(self.preview_layout)
        preview_layout.addStretch(1)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        content_layout.addWidget(left_panel, 2)
        content_layout.addWidget(preview_panel, 1)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidget(content)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        self.create_button = QPushButton("新增任務")
        self.create_button.setObjectName("PrimaryButton")
        self.create_button.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.cancel_button)
        footer.addWidget(self.create_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.scroll_area)
        layout.addLayout(footer)

        self.resize(980, 560)
        self.mode_combo.currentTextChanged.connect(self._sync_schedule_mode)
        self.start_edit.dateTimeChanged.connect(lambda _value: self._render_preview())
        self.review_count_spin.valueChanged.connect(lambda _value: self._sync_schedule_mode())
        for edit in self.manual_time_edits:
            edit.dateTimeChanged.connect(lambda _value: self._render_preview())
        self._sync_schedule_mode()

    def set_categories(self, categories: list[str]) -> None:
        self.category_edit.clear()
        self.category_edit.addItems(categories)
        self.category_edit.setEditable(True)

    def _sync_schedule_mode(self, *_args: object) -> None:
        is_manual = self.mode_combo.currentText() == "手動輸入"
        for index, row in enumerate(self.manual_time_rows):
            row.setVisible(is_manual and index < self.review_count_spin.value())
        self.manual_times_widget.setVisible(is_manual)
        self._render_preview()

    def _render_preview(self) -> None:
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        try:
            times = self.preview_review_times()
        except ValueError as exc:
            label = QLabel(str(exc))
            label.setObjectName("Muted")
            self.preview_layout.addWidget(label)
            return
        start_time = self._start_time()
        for index, remind_time in enumerate(times, start=1):
            row = QFrame()
            row.setObjectName("PreviewRow")
            layout = QHBoxLayout(row)
            badge = QLabel(str(index))
            badge.setObjectName("CountPill")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedWidth(48)
            layout.addWidget(badge)
            text = QLabel(
                f"{remind_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"開始後 {max((remind_time.date() - start_time.date()).days, 0)} 天"
            )
            text.setWordWrap(True)
            layout.addWidget(text, 1)
            self.preview_layout.addWidget(row)

    def preview_review_times(self) -> list[dt.datetime]:
        start_time = self._start_time()
        if self.mode_combo.currentText() == "遺忘曲線":
            return generated_review_times(start_time, self.review_count_spin.value())
        return self.manual_review_times()

    def manual_review_times(self) -> list[dt.datetime]:
        values: list[dt.datetime] = []
        for edit in self.manual_time_edits[: self.review_count_spin.value()]:
            value = edit.dateTime().toPython()
            if isinstance(value, dt.datetime) and value.tzinfo is not None:
                value = value.replace(tzinfo=None)
            values.append(value)
        return validate_manual_review_times(values, self.review_count_spin.value())

    def _start_time(self) -> dt.datetime:
        start_time = self.start_edit.dateTime().toPython()
        if isinstance(start_time, dt.datetime) and start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        return start_time

    def values(self) -> dict[str, object]:
        start_time = self._start_time()
        return {
            "title": self.title_edit.text().strip(),
            "category": self.category_edit.currentText().strip(),
            "difficulty": self.difficulty_combo.currentText(),
            "notes": self.notes_edit.toPlainText().strip(),
            "reminder_method": self.mode_combo.currentText(),
            "start_time": start_time,
            "review_count": self.review_count_spin.value(),
            "review_times": self.preview_review_times(),
        }


class DataDialog(QDialog):
    import_legacy_csv_button = None
    export_full_backup_button = None
    import_full_backup_button = None
    _responsive_size = {
        "preferred_width": 920,
        "preferred_height": 560,
        "minimum_width": 720,
        "minimum_height": 460,
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("報表 / 資料")
        fit_window_to_screen(self, **self._responsive_size)

        description = QLabel(
            "這裡只保留三個主要入口。CSV 用於舊版資料轉移，完整資料請使用 ZIP。"
        )
        description.setWordWrap(True)

        self.import_legacy_csv_button = QPushButton("1. 匯入舊版 CSV")
        self.export_full_backup_button = QPushButton("2. 匯出完整資料")
        self.import_full_backup_button = QPushButton("3. 匯入完整資料")
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(36, 36)
        self.close_button.clicked.connect(self.accept)

        self.legacy_csv_hint = QLabel("請上傳舊版 Forgetting Curve 匯出的 .csv。")
        self.legacy_csv_hint.setWordWrap(True)
        self.full_export_hint = QLabel(
            "會下載 .zip，包含 SQLite 資料庫、背景、貼圖與個人化設定。"
        )
        self.full_export_hint.setWordWrap(True)
        self.full_import_hint = QLabel(
            "請上傳 v8 完整資料包 .zip；系統會先驗證再替換目前資料。"
        )
        self.full_import_hint.setWordWrap(True)

        header = QHBoxLayout()
        title = QLabel("報表 / 資料")
        title.setStyleSheet("font-size: 24px; font-weight: 800;")
        header.addWidget(title, 1)
        header.addWidget(self.close_button)

        actions_panel = QFrame()
        actions_panel.setObjectName("Panel")
        actions_layout = QVBoxLayout(actions_panel)
        actions_title = QLabel("資料操作")
        actions_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        actions_layout.addWidget(actions_title)
        actions_layout.addWidget(description)
        actions_layout.addWidget(self.import_legacy_csv_button)
        actions_layout.addWidget(self.legacy_csv_hint)
        actions_layout.addWidget(self.export_full_backup_button)
        actions_layout.addWidget(self.full_export_hint)
        actions_layout.addWidget(self.import_full_backup_button)
        actions_layout.addWidget(self.full_import_hint)
        warning = QLabel(
            "CSV 只給舊版資料轉移使用；完整備份與還原請使用 ZIP，避免傳錯格式。"
        )
        warning.setWordWrap(True)
        warning.setObjectName("WarningNote")
        actions_layout.addWidget(warning)
        actions_layout.addStretch(1)

        stats_panel = QFrame()
        stats_panel.setObjectName("Panel")
        stats_layout = QVBoxLayout(stats_panel)
        stats_title = QLabel("前 7 天總完成率")
        stats_title.setStyleSheet("font-size: 22px; font-weight: 800;")
        stats_layout.addWidget(stats_title)
        weekly_note = QLabel(
            "計算方式：前 7 天所有到期提醒加總後，以完成數 / 應完成數計算。"
        )
        weekly_note.setWordWrap(True)
        stats_layout.addWidget(weekly_note)
        self.weekly_rate_value = QLabel("--")
        self.weekly_rate_value.setStyleSheet("font-size: 42px; font-weight: 900;")
        self.weekly_fraction_label = QLabel("尚未載入統計")
        self.weekly_fraction_label.setObjectName("Muted")
        stats_layout.addWidget(self.weekly_rate_value)
        stats_layout.addWidget(self.weekly_fraction_label)

        self.total_tasks_value = QLabel("0")
        self.today_reminders_value = QLabel("0")
        self.pending_reminders_value = QLabel("0")
        self.completed_reminders_value = QLabel("0")
        self.total_completion_value = QLabel("0%")
        metric_row = QHBoxLayout()
        metric_row.addWidget(self._metric_card("全部任務", self.total_tasks_value))
        metric_row.addWidget(self._metric_card("今日任務", self.today_reminders_value))
        metric_row.addWidget(self._metric_card("總完成率", self.total_completion_value))
        stats_layout.addLayout(metric_row)

        reminder_row = QHBoxLayout()
        reminder_row.addWidget(
            self._metric_card("未完成提醒", self.pending_reminders_value)
        )
        reminder_row.addWidget(
            self._metric_card("已完成提醒", self.completed_reminders_value)
        )
        stats_layout.addLayout(reminder_row)
        stats_layout.addStretch(1)

        body_container = QWidget()
        body = QHBoxLayout(body_container)
        self.body_layout = body
        body.addWidget(stats_panel, 1)
        body.addWidget(actions_panel, 1)
        self.body_scroll = QScrollArea()
        self.body_scroll.setWidgetResizable(True)
        self.body_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.body_scroll.setWidget(body_container)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.body_scroll)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        fit_window_to_screen(self, **self._responsive_size)

    def set_report_summary(
        self,
        stats: ReportStats,
        *,
        weekly_completed: int,
        weekly_total: int,
        weekly_rate: float,
    ) -> None:
        self.total_tasks_value.setText(str(stats.total_tasks))
        self.today_reminders_value.setText(str(stats.today_reminders))
        self.pending_reminders_value.setText(str(stats.pending_reminders))
        self.completed_reminders_value.setText(str(stats.completed_reminders))
        self.total_completion_value.setText(f"{stats.total_completion_percent:.0f}%")
        self.weekly_rate_value.setText(f"{weekly_rate:.0f}%")
        self.weekly_fraction_label.setText(
            f"{weekly_completed} / {weekly_total} 筆提醒已完成"
        )

    def _metric_card(self, title: str, value_label: QLabel) -> QFrame:
        card = QFrame()
        card.setObjectName("Panel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        label = QLabel(title)
        label.setObjectName("Muted")
        value_label.setStyleSheet("font-size: 24px; font-weight: 800;")
        layout.addWidget(label)
        layout.addWidget(value_label)
        return card

    def choose_csv_open(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "匯入舊版 CSV",
            "",
            "CSV files (*.csv)",
        )
        return Path(path) if path else None

    def choose_zip_open(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "匯入完整資料",
            "",
            "ZIP files (*.zip)",
        )
        return Path(path) if path else None

    def choose_zip_save(self) -> Path | None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出完整資料",
            "",
            "ZIP files (*.zip)",
        )
        return Path(path) if path else None

    def choose_csv_save(self) -> Path | None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出 CSV 備份",
            "",
            "CSV files (*.csv)",
        )
        return Path(path) if path else None


class ImportExportDialog(DataDialog):
    pass
