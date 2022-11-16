import sys, os
import pandas as pd
import numpy as np
from PyQt5.QtGui import *
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtWidgets import QMdiArea, QMdiSubWindow, QTextEdit, QComboBox, QLayout
from NiChart.core.dataio import DataIO
from NiChart.core.baseplugin import BasePlugin
from NiChart.core import iStagingLogger
from NiChart.core.gui.SearchableQComboBox import SearchableQComboBox
from NiChart.core.gui.CheckableQComboBox import CheckableQComboBox
from NiChart.core.plotcanvas import PlotCanvas
from NiChart.core.model.datamodel import PandasModel

logger = iStagingLogger.get_logger(__name__)

class DsetView(QtWidgets.QWidget,BasePlugin):

    def __init__(self):
        super(DsetView,self).__init__()
        
        ## Array that keeps all datasets
        ## All plugins point to the same data_model_arr
        ## Initialized by the mainwindow during loading of plugin
        self.data_model_arr = None

        ## Array that keeps all commands (used in notebook creation)
        self.cmds = None
        
        ## Index of curr dataset
        self.active_index = -1

        ## Read path
        root = os.path.dirname(__file__)
        self.readAdditionalInformation(root)
        
        ## Load ui file
        self.ui = uic.loadUi(os.path.join(root, 'dsetview.ui'),self)
        
        ## Main view panel
        self.mdi = self.findChild(QMdiArea, 'mdiArea')       
        self.mdi.setBackground(QtGui.QColor(245,245,245,255))

        ## Panel for dataset selection
        self.ui.comboBoxDsets = QComboBox(self.ui)
        self.ui.comboBoxDsets.setEditable(False)        
        self.ui.vlComboDSets.addWidget(self.ui.comboBoxDsets)
        
        ## Panel for sorting
        self.ui.comboBoxSortCat1 = QComboBox(self.ui)
        self.ui.vlComboSort1.addWidget(self.ui.comboBoxSortCat1)
        self.ui.comboBoxSortCat1.setCurrentIndex(-1)
        
        self.ui.comboBoxSortVar1 = SearchableQComboBox(self.ui)
        self.ui.vlComboSort1.addWidget(self.ui.comboBoxSortVar1)

        self.ui.comboBoxSortCat2 = QComboBox(self.ui)
        self.ui.vlComboSort2.addWidget(self.ui.comboBoxSortCat2)

        self.ui.comboBoxSortVar2 = SearchableQComboBox(self.ui)
        self.ui.vlComboSort2.addWidget(self.ui.comboBoxSortVar2)       

        ## Options panel is not shown initially 
        ## Shown when a dataset is loaded
        self.ui.wOptions.hide()
    
    def SetupConnections(self):
        self.data_model_arr.active_dset_changed.connect(self.OnDataChanged)

        self.ui.showTableBtn.clicked.connect(self.OnShowTableBtnClicked)
        self.ui.showDictBtn.clicked.connect(self.OnShowDictBtnClicked)
        self.ui.comboBoxDsets.currentIndexChanged.connect(self.OnDataSelectionChanged)
        self.ui.comboBoxSortCat1.currentIndexChanged.connect(self.OnSortCat1Changed)
        self.ui.comboBoxSortCat2.currentIndexChanged.connect(self.OnSortCat2Changed)


    def OnShowDictBtnClicked(self):      
        tmpDict = self.data_model_arr.data_dict.reset_index()
        self.PopulateTable(tmpDict)         ## Show dict in a table
        
        sub = QMdiSubWindow()
        sub.setWidget(self.dataView)
        self.mdi.addSubWindow(sub)        
        sub.show()
        self.mdi.tileSubWindows()

    def OnShowTableBtnClicked(self):
        currDset = self.ui.comboBoxDsets.currentText()
        
        ##-------
        ## Set data sorting order
        sortCols = []
        sortOrders = []
        if self.ui.check_sort1.isChecked():
            sortCols.append(self.ui.comboBoxSortVar1.currentText())
            if self.ui.check_asc1.isChecked():
                sortOrders.append(True)
            else:   
                sortOrders.append(False)
        if self.ui.check_sort2.isChecked():
            sortCols.append(self.ui.comboBoxSortVar2.currentText())
            if self.ui.check_asc2.isChecked():
                sortOrders.append(True)
            else:
                sortOrders.append(False)
        ##-------

        ## Apply the sorting
        if len(sortCols)>0:

            # Variables required for preparing the notebook command
            dset_name = self.data_model_arr.dataset_names[self.active_index]       
            str_sortCols = ','.join('"{0}"'.format(x) for x in sortCols)
            str_sortOrders = ','.join('"{0}"'.format(x) for x in sortOrders)

            logger.info('Sorting data by : ' + str_sortCols)

            # Get active dset, apply sort, reassign it
            dtmp = self.data_model_arr.datasets[self.active_index].data
            dtmp = dtmp.sort_values(sortCols, ascending=sortOrders)
            self.data_model_arr.datasets[self.active_index].data = dtmp
            

        ## Load data to data view
        tmpData = self.data_model_arr.datasets[self.active_index].data
        self.PopulateTable(tmpData)

        ## Set data view to mdi widget
        sub = QMdiSubWindow()
        sub.setWidget(self.dataView)
        self.mdi.addSubWindow(sub)        
        sub.show()
        self.mdi.tileSubWindows()
        
        ##-------
        ## Populate commands that will be written in a notebook
        cmds = ['']
        if len(sortCols)>0:
            cmds.append(dset_name + ' = ' + dset_name + '.sort_values([' + 
                             str_sortCols  + '], ascending = [' + str_sortOrders + '])')
        cmds.append(dset_name + '.head()')
        cmds.append('')
        self.cmds.add_cmds(cmds)
        ##-------

    def PopulateTable(self, data):
        model = PandasModel(data)
        self.dataView = QtWidgets.QTableView()
        self.dataView.setModel(model)

    def PopulateComboBox(self, cbox, values, strPlaceholder = None, currTxt = None):
        cbox.blockSignals(True)
        cbox.clear()

        ## Add values to combo box
        cbox.addItems(values)
        
        ## Add a first row with placeholder text to the combo box
        if strPlaceholder is not None:
            cbox.setCurrentIndex(-1)
            cbox.setEditable(True)
            cbox.setCurrentText(strPlaceholder)
        
        ## Set the current text in the combo box
        if currTxt is not None:
            cbox.setCurrentText(currTxt)
        cbox.blockSignals(False)
        
    def OnSortCat1Changed(self):
        
        ## Read selected variable category, find variables in that category, add them to combo box
        selCat = self.ui.comboBoxSortCat1.currentText()
        tmpData = self.data_model_arr.datasets[self.active_index]
        selVars = tmpData.data_cat_map.loc[[selCat]].VarName.tolist()
        self.PopulateComboBox(self.ui.comboBoxSortVar1, selVars)

    def OnSortCat2Changed(self):

        ## Read selected variable category, find variables in that category, add them to combo box
        selCat = self.ui.comboBoxSortCat2.currentText()
        tmpData = self.data_model_arr.datasets[self.active_index]
        selVars = tmpData.data_cat_map.loc[[selCat]].VarName.tolist()
        self.PopulateComboBox(self.ui.comboBoxSortVar2, selVars)


    def OnDataChanged(self):
        
        logger.info('Data changed')

        ## Make options panel visible
        self.ui.wOptions.show()

        ## Set visibility for parts of options panel
        if self.data_model_arr.data_dict is None:
            self.ui.wShowDict.hide()
        else:
            self.ui.wShowDict.show()

        if len(self.data_model_arr.datasets) == 0:
            self.ui.wActiveDset.hide()
            self.ui.wSorting.hide()
            self.ui.wShowTable.hide()
        else:
            self.ui.wActiveDset.show()
            self.ui.wSorting.show()
            self.ui.wShowTable.show()

        ## Set fields for various options
        self.active_index = self.data_model_arr.active_index
        if self.active_index >= 0:
            
            ## Get data variables
            dataset = self.data_model_arr.datasets[self.active_index]

            colNames = dataset.data.columns.tolist()
            dsetName = dataset.file_name
            dsetShape = dataset.data.shape
            catNames = dataset.data_cat_map.index.unique().tolist()
            dataset_names = self.data_model_arr.dataset_names

            ## Set data info fields
            self.ui.edit_fname.setText(os.path.basename(dsetName))
            self.ui.edit_dshape.setText(str(dsetShape))

            ## Update sorting panel
            self.UpdateSortingPanel(catNames, colNames)
            
            ## Update dataset selection
            self.PopulateComboBox(self.ui.comboBoxDsets, dataset_names, currTxt = dataset_names[self.active_index])

    def UpdateSortingPanel(self, catNames, colNames):
        
        ## Uncheck edit boxes
        self.ui.check_sort1.setChecked(False)
        self.ui.check_asc1.setChecked(False)
        self.ui.check_sort2.setChecked(False)
        self.ui.check_asc2.setChecked(False)
        
        if len(catNames) == 1:      ## Single variable category, no need for category combobox
            self.ui.comboBoxSortCat1.hide()
            self.ui.comboBoxSortCat2.hide()
        else:
            self.ui.comboBoxSortCat1.show()
            self.ui.comboBoxSortCat2.show()
            self.PopulateComboBox(self.ui.comboBoxSortCat1, catNames, '--var group--')
            self.PopulateComboBox(self.ui.comboBoxSortCat2, catNames, '--var group--')
        self.PopulateComboBox(self.ui.comboBoxSortVar1, colNames, '--var name--')
        self.PopulateComboBox(self.ui.comboBoxSortVar2, colNames, '--var name--')

    def OnDataSelectionChanged(self):
        
        logger.info('Dataset selection changed')

        ## Set current dataset
        selDsetName = self.ui.comboBoxDsets.currentText()
        self.active_index = np.where(np.array(self.data_model_arr.dataset_names) == selDsetName)[0][0]
        self.data_model_arr.active_index = self.active_index
        
        self.data_model_arr.OnDataChanged()
        