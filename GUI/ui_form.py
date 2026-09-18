# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QPlainTextEdit, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

from GUI.widgets import GlowTabWidget

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1120, 850)
        MainWindow.setMinimumSize(QSize(780, 640))
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.rootLayout = QVBoxLayout(self.centralwidget)
        self.rootLayout.setSpacing(0)
        self.rootLayout.setObjectName(u"rootLayout")
        self.rootLayout.setContentsMargins(0, 0, 0, 0)
        self.header = QFrame(self.centralwidget)
        self.header.setObjectName(u"header")
        self.headerLayout = QHBoxLayout(self.header)
        self.headerLayout.setSpacing(16)
        self.headerLayout.setObjectName(u"headerLayout")
        self.headerLayout.setContentsMargins(32, 18, 32, 18)
        self.brandLabel = QLabel(self.header)
        self.brandLabel.setObjectName(u"brandLabel")
        self.brandLabel.setWordWrap(True)

        self.headerLayout.addWidget(self.brandLabel)

        self.taglineLabel = QLabel(self.header)
        self.taglineLabel.setObjectName(u"taglineLabel")
        self.taglineLabel.setWordWrap(True)

        self.headerLayout.addWidget(self.taglineLabel)

        self.headerSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.headerLayout.addItem(self.headerSpacer)

        self.previewBadge = QLabel(self.header)
        self.previewBadge.setObjectName(u"previewBadge")
        self.previewBadge.setWordWrap(False)

        self.headerLayout.addWidget(self.previewBadge)


        self.rootLayout.addWidget(self.header)

        self.workspaceScroll = QScrollArea(self.centralwidget)
        self.workspaceScroll.setObjectName(u"workspaceScroll")
        self.workspaceScroll.setWidgetResizable(True)
        self.workspace = QWidget()
        self.workspace.setObjectName(u"workspace")
        self.workspace.setGeometry(QRect(0, 0, 1103, 921))
        self.workspaceLayout = QVBoxLayout(self.workspace)
        self.workspaceLayout.setSpacing(20)
        self.workspaceLayout.setObjectName(u"workspaceLayout")
        self.workspaceLayout.setContentsMargins(32, 28, 32, 24)
        self.titleLabel = QLabel(self.workspace)
        self.titleLabel.setObjectName(u"titleLabel")
        self.titleLabel.setWordWrap(True)

        self.workspaceLayout.addWidget(self.titleLabel)

        self.subtitleLabel = QLabel(self.workspace)
        self.subtitleLabel.setObjectName(u"subtitleLabel")
        self.subtitleLabel.setWordWrap(True)

        self.workspaceLayout.addWidget(self.subtitleLabel)

        self.columnsLayout = QHBoxLayout()
        self.columnsLayout.setSpacing(20)
        self.columnsLayout.setObjectName(u"columnsLayout")
        self.inputCard = QFrame(self.workspace)
        self.inputCard.setObjectName(u"inputCard")
        self.inputLayout = QVBoxLayout(self.inputCard)
        self.inputLayout.setSpacing(16)
        self.inputLayout.setObjectName(u"inputLayout")
        self.inputLayout.setContentsMargins(22, 22, 22, 22)
        self.formatLayout = QHBoxLayout()
        self.formatLayout.setSpacing(16)
        self.formatLayout.setObjectName(u"formatLayout")
        self.inputHeading = QLabel(self.inputCard)
        self.inputHeading.setObjectName(u"inputHeading")
        self.inputHeading.setWordWrap(True)

        self.formatLayout.addWidget(self.inputHeading)

        self.formatSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.formatLayout.addItem(self.formatSpacer)

        self.formatLabel = QLabel(self.inputCard)
        self.formatLabel.setObjectName(u"formatLabel")
        self.formatLabel.setWordWrap(True)

        self.formatLayout.addWidget(self.formatLabel)

        self.formatCombo = QComboBox(self.inputCard)
        self.formatCombo.addItem("")
        self.formatCombo.addItem("")
        self.formatCombo.setObjectName(u"formatCombo")

        self.formatLayout.addWidget(self.formatCombo)


        self.inputLayout.addLayout(self.formatLayout)

        self.inputTabs = GlowTabWidget(self.inputCard)
        self.inputTabs.setObjectName(u"inputTabs")
        self.textPage = QWidget()
        self.textPage.setObjectName(u"textPage")
        self.textLayout = QVBoxLayout(self.textPage)
        self.textLayout.setSpacing(6)
        self.textLayout.setObjectName(u"textLayout")
        self.textLayout.setContentsMargins(0, 16, 0, 0)
        self.editorHint = QLabel(self.textPage)
        self.editorHint.setObjectName(u"editorHint")
        self.editorHint.setWordWrap(True)

        self.textLayout.addWidget(self.editorHint)

        self.modelEditor = QPlainTextEdit(self.textPage)
        self.modelEditor.setObjectName(u"modelEditor")
        self.modelEditor.setMinimumSize(QSize(0, 255))

        self.textLayout.addWidget(self.modelEditor)

        self.editorFooterLayout = QHBoxLayout()
        self.editorFooterLayout.setSpacing(6)
        self.editorFooterLayout.setObjectName(u"editorFooterLayout")
        self.characterCount = QLabel(self.textPage)
        self.characterCount.setObjectName(u"characterCount")
        self.characterCount.setWordWrap(False)

        self.editorFooterLayout.addWidget(self.characterCount)

        self.editorSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.editorFooterLayout.addItem(self.editorSpacer)

        self.exampleButton = QPushButton(self.textPage)
        self.exampleButton.setObjectName(u"exampleButton")

        self.editorFooterLayout.addWidget(self.exampleButton)

        self.clearButton = QPushButton(self.textPage)
        self.clearButton.setObjectName(u"clearButton")

        self.editorFooterLayout.addWidget(self.clearButton)


        self.textLayout.addLayout(self.editorFooterLayout)

        self.inputTabs.addTab(self.textPage, "")
        self.uploadPage = QWidget()
        self.uploadPage.setObjectName(u"uploadPage")
        self.uploadLayout = QVBoxLayout(self.uploadPage)
        self.uploadLayout.setSpacing(6)
        self.uploadLayout.setObjectName(u"uploadLayout")
        self.uploadLayout.setContentsMargins(0, 16, 0, 0)
        self.dropZone = QFrame(self.uploadPage)
        self.dropZone.setObjectName(u"dropZone")
        self.dropZone.setMinimumSize(QSize(0, 260))
        self.dropZone.setAcceptDrops(True)
        self.dropLayout = QVBoxLayout(self.dropZone)
        self.dropLayout.setSpacing(6)
        self.dropLayout.setObjectName(u"dropLayout")
        self.dropLayout.setContentsMargins(28, 30, 28, 30)
        self.dropTopSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.dropLayout.addItem(self.dropTopSpacer)

        self.uploadSymbol = QLabel(self.dropZone)
        self.uploadSymbol.setObjectName(u"uploadSymbol")
        self.uploadSymbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.uploadSymbol.setWordWrap(True)

        self.dropLayout.addWidget(self.uploadSymbol, 0, Qt.AlignmentFlag.AlignHCenter)

        self.dropHeading = QLabel(self.dropZone)
        self.dropHeading.setObjectName(u"dropHeading")
        self.dropHeading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dropHeading.setWordWrap(True)

        self.dropLayout.addWidget(self.dropHeading)

        self.dropHint = QLabel(self.dropZone)
        self.dropHint.setObjectName(u"dropHint")
        self.dropHint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dropHint.setWordWrap(True)

        self.dropLayout.addWidget(self.dropHint)

        self.browseButton = QPushButton(self.dropZone)
        self.browseButton.setObjectName(u"browseButton")

        self.dropLayout.addWidget(self.browseButton, 0, Qt.AlignmentFlag.AlignHCenter)

        self.supportedFormats = QLabel(self.dropZone)
        self.supportedFormats.setObjectName(u"supportedFormats")
        self.supportedFormats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.supportedFormats.setWordWrap(True)

        self.dropLayout.addWidget(self.supportedFormats)

        self.dropBottomSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.dropLayout.addItem(self.dropBottomSpacer)


        self.uploadLayout.addWidget(self.dropZone)

        self.fileLayout = QHBoxLayout()
        self.fileLayout.setSpacing(16)
        self.fileLayout.setObjectName(u"fileLayout")
        self.fileLabel = QLabel(self.uploadPage)
        self.fileLabel.setObjectName(u"fileLabel")
        self.fileLabel.setWordWrap(True)

        self.fileLayout.addWidget(self.fileLabel)

        self.removeButton = QPushButton(self.uploadPage)
        self.removeButton.setObjectName(u"removeButton")
        self.removeButton.setEnabled(False)

        self.fileLayout.addWidget(self.removeButton)

        self.fileLayout.setStretch(0, 1)

        self.uploadLayout.addLayout(self.fileLayout)

        self.inputTabs.addTab(self.uploadPage, "")

        self.inputLayout.addWidget(self.inputTabs)

        self.actionLayout = QHBoxLayout()
        self.actionLayout.setSpacing(16)
        self.actionLayout.setObjectName(u"actionLayout")
        self.analysisHint = QLabel(self.inputCard)
        self.analysisHint.setObjectName(u"analysisHint")
        self.analysisHint.setWordWrap(True)

        self.actionLayout.addWidget(self.analysisHint)

        self.analyzeButton = QPushButton(self.inputCard)
        self.analyzeButton.setObjectName(u"analyzeButton")
        self.analyzeButton.setEnabled(False)

        self.actionLayout.addWidget(self.analyzeButton)

        self.actionLayout.setStretch(0, 1)

        self.inputLayout.addLayout(self.actionLayout)


        self.columnsLayout.addWidget(self.inputCard)

        self.guideCard = QFrame(self.workspace)
        self.guideCard.setObjectName(u"guideCard")
        self.guideCard.setMaximumSize(QSize(270, 16777215))
        self.guideLayout = QVBoxLayout(self.guideCard)
        self.guideLayout.setSpacing(16)
        self.guideLayout.setObjectName(u"guideLayout")
        self.guideLayout.setContentsMargins(22, 22, 22, 22)
        self.guideHeading = QLabel(self.guideCard)
        self.guideHeading.setObjectName(u"guideHeading")
        self.guideHeading.setWordWrap(True)

        self.guideLayout.addWidget(self.guideHeading)

        self.reactionHeading = QLabel(self.guideCard)
        self.reactionHeading.setObjectName(u"reactionHeading")
        self.reactionHeading.setWordWrap(True)

        self.guideLayout.addWidget(self.reactionHeading)

        self.reactionHelp = QLabel(self.guideCard)
        self.reactionHelp.setObjectName(u"reactionHelp")
        self.reactionHelp.setWordWrap(True)

        self.guideLayout.addWidget(self.reactionHelp)

        self.odeHeading = QLabel(self.guideCard)
        self.odeHeading.setObjectName(u"odeHeading")
        self.odeHeading.setWordWrap(True)

        self.guideLayout.addWidget(self.odeHeading)

        self.odeHelp = QLabel(self.guideCard)
        self.odeHelp.setObjectName(u"odeHelp")
        self.odeHelp.setWordWrap(True)

        self.guideLayout.addWidget(self.odeHelp)

        self.fileHeading = QLabel(self.guideCard)
        self.fileHeading.setObjectName(u"fileHeading")
        self.fileHeading.setWordWrap(True)

        self.guideLayout.addWidget(self.fileHeading)

        self.fileHelp = QLabel(self.guideCard)
        self.fileHelp.setObjectName(u"fileHelp")
        self.fileHelp.setWordWrap(True)

        self.guideLayout.addWidget(self.fileHelp)

        self.guideSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.guideLayout.addItem(self.guideSpacer)


        self.columnsLayout.addWidget(self.guideCard)

        self.columnsLayout.setStretch(0, 3)
        self.columnsLayout.setStretch(1, 1)

        self.workspaceLayout.addLayout(self.columnsLayout)

        self.resultsCard = QFrame(self.workspace)
        self.resultsCard.setObjectName(u"resultsCard")
        self.resultsLayout = QVBoxLayout(self.resultsCard)
        self.resultsLayout.setSpacing(6)
        self.resultsLayout.setObjectName(u"resultsLayout")
        self.resultsLayout.setContentsMargins(22, 20, 22, 20)
        self.resultsHeading = QLabel(self.resultsCard)
        self.resultsHeading.setObjectName(u"resultsHeading")
        self.resultsHeading.setWordWrap(True)

        self.resultsLayout.addWidget(self.resultsHeading)

        self.resultsEmptyTitle = QLabel(self.resultsCard)
        self.resultsEmptyTitle.setObjectName(u"resultsEmptyTitle")
        self.resultsEmptyTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resultsEmptyTitle.setWordWrap(True)

        self.resultsLayout.addWidget(self.resultsEmptyTitle)

        self.resultsMetrics = QLabel(self.resultsCard)
        self.resultsMetrics.setObjectName(u"resultsMetrics")
        self.resultsMetrics.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resultsMetrics.setWordWrap(True)

        self.resultsLayout.addWidget(self.resultsMetrics)

        self.resultsHint = QLabel(self.resultsCard)
        self.resultsHint.setObjectName(u"resultsHint")
        self.resultsHint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resultsHint.setWordWrap(True)

        self.resultsLayout.addWidget(self.resultsHint)

        self.analysisTabs = GlowTabWidget(self.resultsCard)
        self.analysisTabs.setObjectName(u"analysisTabs")
        self.analysisTabs.setMinimumSize(QSize(0, 600))
        self.reportPage = QWidget()
        self.reportPage.setObjectName(u"reportPage")
        self.reportLayout = QVBoxLayout(self.reportPage)
        self.reportLayout.setObjectName(u"reportLayout")
        self.resultReport = QPlainTextEdit(self.reportPage)
        self.resultReport.setObjectName(u"resultReport")
        self.resultReport.setReadOnly(True)
        self.resultReport.setMinimumSize(QSize(0, 220))

        self.reportLayout.addWidget(self.resultReport)

        self.analysisTabs.addTab(self.reportPage, "")
        self.reactionGraphPage = QWidget()
        self.reactionGraphPage.setObjectName(u"reactionGraphPage")
        font = QFont()
        font.setBold(True)
        self.reactionGraphPage.setFont(font)
        self.reactionGraphLayout = QVBoxLayout(self.reactionGraphPage)
        self.reactionGraphLayout.setObjectName(u"reactionGraphLayout")
        self.reactionGraphHint = QLabel(self.reactionGraphPage)
        self.reactionGraphHint.setObjectName(u"reactionGraphHint")
        self.reactionGraphHint.setWordWrap(True)
        font1 = QFont()
        font1.setBold(False)
        self.reactionGraphHint.setFont(font1)

        self.reactionGraphLayout.addWidget(self.reactionGraphHint)

        self.analysisTabs.addTab(self.reactionGraphPage, "")
        self.linkageGraphPage = QWidget()
        self.linkageGraphPage.setObjectName(u"linkageGraphPage")
        self.linkageGraphPage.setFont(font)
        self.linkageGraphLayout = QVBoxLayout(self.linkageGraphPage)
        self.linkageGraphLayout.setObjectName(u"linkageGraphLayout")
        self.linkageGraphHint = QLabel(self.linkageGraphPage)
        self.linkageGraphHint.setObjectName(u"linkageGraphHint")
        self.linkageGraphHint.setWordWrap(True)
        self.linkageGraphHint.setFont(font1)

        self.linkageGraphLayout.addWidget(self.linkageGraphHint)

        self.analysisTabs.addTab(self.linkageGraphPage, "")

        self.resultsLayout.addWidget(self.analysisTabs)


        self.workspaceLayout.addWidget(self.resultsCard)

        self.statusLabel = QLabel(self.workspace)
        self.statusLabel.setObjectName(u"statusLabel")
        self.statusLabel.setWordWrap(True)

        self.workspaceLayout.addWidget(self.statusLabel)

        self.bodySpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.workspaceLayout.addItem(self.bodySpacer)

        self.workspaceScroll.setWidget(self.workspace)

        self.rootLayout.addWidget(self.workspaceScroll)

        MainWindow.setCentralWidget(self.centralwidget)
        QWidget.setTabOrder(self.formatCombo, self.inputTabs)
        QWidget.setTabOrder(self.inputTabs, self.modelEditor)
        QWidget.setTabOrder(self.modelEditor, self.exampleButton)
        QWidget.setTabOrder(self.exampleButton, self.clearButton)
        QWidget.setTabOrder(self.clearButton, self.browseButton)
        QWidget.setTabOrder(self.browseButton, self.removeButton)
        QWidget.setTabOrder(self.removeButton, self.analyzeButton)

        self.retranslateUi(MainWindow)
        self.clearButton.clicked.connect(self.modelEditor.clear)

        self.inputTabs.setCurrentIndex(1)
        self.analysisTabs.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"CRNTAnalysis \u2022 Model workspace", None))
        MainWindow.setStyleSheet(QCoreApplication.translate("MainWindow", u"\n"
"QWidget { font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; font-size: 14px;\n"
"          color: #22334a; background: #f4f6fa; }\n"
"QFrame#header, QFrame#inputCard, QFrame#guideCard, QFrame#resultsCard { background: white; border: 1px solid #e0e6ef; border-radius: 12px; }\n"
"QFrame#header { border-radius: 0; border: none; border-bottom: 1px solid #e0e6ef; }\n"
"QWidget#textPage, QWidget#uploadPage { background: white; }\n"
"QLabel { background: transparent; }\n"
"QLabel#brandLabel { font-size: 19px; font-weight: 700; }\n"
"QLabel#titleLabel { font-size: 29px; font-weight: 700; }\n"
"QLabel#subtitle, QLabel#unusedMuted { color: #69788d; }\n"
"QLabel#unusedSection { font-size: 17px; font-weight: 600; }\n"
"QLabel#previewBadge { color: #397d74; background: #eaf5f1; border-radius: 10px; padding: 6px 12px; }\n"
"QLabel#uploadSymbol { color: #246dce; background: #edf4ff; border-radius: 12px; font-size: 25px; padding: 10px; }\n"
"QPushButton { background: white; border: 1px solid #d6deea; border-radius: "
                        "7px; padding: 9px 16px; font-weight: 600; }\n"
"QPushButton:hover { background: #edf4ff; border-color: #a6c4ef; }\n"
"QPushButton:pressed { background: #deebff; }\n"
"QPushButton#analyzeButton { background: #246dce; color: white; border: none; }\n"
"QPushButton#analyzeButton:disabled { background: #e9edf3; color: #8b97a7; }\n"
"QPushButton#analyzeButton:hover { background: #1b5ab0; }\n"
"QPushButton:disabled { background: #e9edf3; color: #8b97a7; border-color: #e1e6ee; }\n"
"QPushButton:focus, QComboBox:focus { border: 2px solid #246dce; }\n"
"QTabWidget::pane { background: white; border: none; }\n"
"QTabBar::tab { background: white; color: #718097; padding: 12px 20px; border-bottom: 2px solid #e5eaf1; }\n"
"QTabBar::tab:selected { color: #246dce; border-bottom: 2px solid #246dce; font-weight: 600; }\n"
"QPlainTextEdit { font-family: 'Menlo', 'Consolas', monospace; background: #fafbfd; border: 1px solid #dfe6f0; border-radius: 8px; padding: 12px; selection-background-color: #c6ddff; }\n"
"QPlainTextEdit:focus "
                        "{ border: 1px solid #246dce; }\n"
"QComboBox { background: white; border: 1px solid #d6deea; border-radius: 6px; padding: 7px 12px; min-width: 145px; }\n"
"QComboBox QAbstractItemView { background: white; selection-background-color: #deebff; }\n"
"QFrame#dropZone { background: #fafcff; border: 2px dashed #bccce2; border-radius: 12px; }\n"
"QFrame#dropZone[active=\"true\"] { background: #edf4ff; border-color: #246dce; }\n"
"QScrollArea { border: none; }\n"
"\n"
"QLabel[role=\"muted\"] { color: #69788d; }\n"
"QLabel[role=\"section\"] { font-size: 17px; font-weight: 600; }\n"
"QLabel#taglineLabel, QLabel#formatLabel, QLabel#editorHint, QLabel#characterCount, QLabel#dropHint, QLabel#supportedFormats, QLabel#fileLabel, QLabel#analysisHint, QLabel#reactionHelp, QLabel#odeHelp, QLabel#fileHelp, QLabel#resultsMetrics, QLabel#resultsHint, QLabel#statusLabel { color: #69788d; }\n"
"QLabel#inputHeading, QLabel#dropHeading, QLabel#guideHeading, QLabel#reactionHeading, QLabel#odeHeading, QLabel#fileHeading, QLabel#resultsH"
                        "eading, QLabel#resultsEmptyTitle { font-size: 17px; font-weight: 600; }\n"
"QLabel#subtitleLabel { color: #69788d; }\n"
"QTabBar::tab:hover { background: #eaf4ff; color: #176cd3; border-bottom: 2px solid #72b7ff; }\n"
"QPushButton:hover { color: #176cd3; }", None))
        self.brandLabel.setText(QCoreApplication.translate("MainWindow", u"CRNTAnalysis", None))
        self.taglineLabel.setText(QCoreApplication.translate("MainWindow", u"Chemical Reaction Network Theory", None))
        self.taglineLabel.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
        self.previewBadge.setText(QCoreApplication.translate("MainWindow", u"Desktop App v1.0", None))
        self.titleLabel.setText(QCoreApplication.translate("MainWindow", u"Your model, ready to explore.", None))
        self.subtitleLabel.setText(QCoreApplication.translate("MainWindow", u"Paste a reaction network or upload a model file to get started.", None))
        self.inputHeading.setText(QCoreApplication.translate("MainWindow", u"01  /  Model input", None))
        self.inputHeading.setProperty(u"role", QCoreApplication.translate("MainWindow", u"section", None))
        self.formatLabel.setText(QCoreApplication.translate("MainWindow", u"Format", None))
        self.formatLabel.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
        self.formatCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"Reaction network", None))
        self.formatCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"ODE model", None))

#if QT_CONFIG(accessibility)
        self.formatCombo.setAccessibleName(QCoreApplication.translate("MainWindow", u"Model input format", None))
#endif // QT_CONFIG(accessibility)
        self.editorHint.setText(QCoreApplication.translate("MainWindow", u"Paste or write your model below.", None))
        self.editorHint.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
#if QT_CONFIG(accessibility)
        self.modelEditor.setAccessibleName(QCoreApplication.translate("MainWindow", u"Model text", None))
#endif // QT_CONFIG(accessibility)
        self.modelEditor.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Reactions:\n"
"X k1-> Y\n"
"Y k2-> X\n"
"\n"
"Rate Constants:\n"
"k1 = 0.5\n"
"k2 = 0.2\n"
"\n"
"Initial Conditions:\n"
"X = 1.0\n"
"Y = 0.0\n"
"", None))
        self.characterCount.setText(QCoreApplication.translate("MainWindow", u"0 lines \u00b7 0 characters", None))
        self.characterCount.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
        self.exampleButton.setText(QCoreApplication.translate("MainWindow", u"Load example", None))
        self.clearButton.setText(QCoreApplication.translate("MainWindow", u"Clear", None))
        self.inputTabs.setTabText(self.inputTabs.indexOf(self.textPage), QCoreApplication.translate("MainWindow", u"Paste text", None))
        self.uploadSymbol.setText(QCoreApplication.translate("MainWindow", u"\u2191", None))
        self.dropHeading.setText(QCoreApplication.translate("MainWindow", u"Drop your model file here", None))
        self.dropHeading.setProperty(u"role", QCoreApplication.translate("MainWindow", u"section", None))
        self.dropHint.setText(QCoreApplication.translate("MainWindow", u"or choose a file from your computer", None))
        self.dropHint.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
        self.browseButton.setText(QCoreApplication.translate("MainWindow", u"Browse files\u2026", None))
        self.supportedFormats.setText(QCoreApplication.translate("MainWindow", u"Supported formats: .react, .ode, .txt", None))
        self.supportedFormats.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
        self.fileLabel.setText(QCoreApplication.translate("MainWindow", u"No file selected", None))
        self.fileLabel.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
        self.removeButton.setText(QCoreApplication.translate("MainWindow", u"Remove", None))
        self.inputTabs.setTabText(self.inputTabs.indexOf(self.uploadPage), QCoreApplication.translate("MainWindow", u"Upload file", None))
        self.analysisHint.setText(QCoreApplication.translate("MainWindow", u"Missing parameter values remain symbolic.", None))
        self.analysisHint.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
#if QT_CONFIG(tooltip)
        self.analyzeButton.setToolTip(QCoreApplication.translate("MainWindow", u"Parse the selected input and calculate network and linkage-class deficiency.", None))
#endif // QT_CONFIG(tooltip)
        self.analyzeButton.setText(QCoreApplication.translate("MainWindow", u"Analyze model  \u2192", None))
        self.guideHeading.setText(QCoreApplication.translate("MainWindow", u"A little guidance", None))
        self.guideHeading.setProperty(u"role", QCoreApplication.translate("MainWindow", u"section", None))
        self.reactionHeading.setText(QCoreApplication.translate("MainWindow", u"Reaction networks", None))
        self.reactionHeading.setProperty(u"role", QCoreApplication.translate("MainWindow", u"section", None))
        self.reactionHelp.setText(QCoreApplication.translate("MainWindow", u"Use a Reactions: section with one reaction per line. Add rate constants and initial conditions as needed.", None))
        self.reactionHelp.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
        self.odeHeading.setText(QCoreApplication.translate("MainWindow", u"ODE models", None))
        self.odeHeading.setProperty(u"role", QCoreApplication.translate("MainWindow", u"section", None))
        self.odeHelp.setText(QCoreApplication.translate("MainWindow", u"Use an ODE Model: section with mass-action equations, followed by a Coefficients: section.", None))
        self.odeHelp.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
        self.fileHeading.setText(QCoreApplication.translate("MainWindow", u"File input", None))
        self.fileHeading.setProperty(u"role", QCoreApplication.translate("MainWindow", u"section", None))
        self.fileHelp.setText(QCoreApplication.translate("MainWindow", u"Select one .react, .ode, or .txt file. For .txt files, choose the matching format above.", None))
        self.fileHelp.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
        self.resultsHeading.setText(QCoreApplication.translate("MainWindow", u"02  /  Analysis overview", None))
        self.resultsHeading.setProperty(u"role", QCoreApplication.translate("MainWindow", u"section", None))
        self.resultsEmptyTitle.setText(QCoreApplication.translate("MainWindow", u"Your network insights will appear here", None))
        self.resultsEmptyTitle.setProperty(u"role", QCoreApplication.translate("MainWindow", u"section", None))
        self.resultsMetrics.setText(QCoreApplication.translate("MainWindow", u"Complexes   \u00b7   Linkage classes   \u00b7   Stoichiometric rank   \u00b7   Deficiency", None))
        self.resultsMetrics.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
        self.resultsHint.setText(QCoreApplication.translate("MainWindow", u"Select an input and click Analyze model.", None))
        self.resultsHint.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
#if QT_CONFIG(accessibility)
        self.resultReport.setAccessibleName(QCoreApplication.translate("MainWindow", u"Analysis report", None))
#endif // QT_CONFIG(accessibility)
        self.analysisTabs.setTabText(self.analysisTabs.indexOf(self.reportPage), QCoreApplication.translate("MainWindow", u"Analysis report", None))
#if QT_CONFIG(tooltip)
        self.reactionGraphPage.setToolTip(QCoreApplication.translate("MainWindow", u"Hover a node to animate its highlight. Click a node to open details; click empty space or press Esc to close.", None))
#endif // QT_CONFIG(tooltip)
        self.reactionGraphHint.setText(QCoreApplication.translate("MainWindow", u"Nodes are complexes (C index: composition). Colors identify linkage classes; the legend shows each class\u2019s deficiency. Arrows show reactions; bold labels show reaction indices and rates. Hover to highlight; click a node for details. Click empty space or press Esc to close. Use the toolbar to pan, zoom, reset, or save.", None))
        self.analysisTabs.setTabText(self.analysisTabs.indexOf(self.reactionGraphPage), QCoreApplication.translate("MainWindow", u"Reaction graph", None))
#if QT_CONFIG(tooltip)
        self.linkageGraphPage.setToolTip(QCoreApplication.translate("MainWindow", u"Hover a node to animate its highlight. Click a node to open details; click empty space or press Esc to close.", None))
#endif // QT_CONFIG(tooltip)
        self.linkageGraphHint.setText(QCoreApplication.translate("MainWindow", u"Nodes are complexes (C index: composition). Colors identify linkage classes; the legend shows each class\u2019s deficiency. Undirected edges connect complexes in the same linkage class. Hover to highlight; click a node for details. Click empty space or press Esc to close. Use the toolbar to pan, zoom, reset, or save.", None))
        self.analysisTabs.setTabText(self.analysisTabs.indexOf(self.linkageGraphPage), QCoreApplication.translate("MainWindow", u"Linkage graph", None))
        self.statusLabel.setText(QCoreApplication.translate("MainWindow", u"Ready \u2022 Paste text or select a model file.", None))
        self.statusLabel.setProperty(u"role", QCoreApplication.translate("MainWindow", u"muted", None))
    # retranslateUi

