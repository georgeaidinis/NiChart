from PyQt5.QtGui import *
from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtWidgets import QMdiArea, QMdiSubWindow, QLineEdit, QComboBox, QMenu, QAction, QWidgetAction
import sys, os
import pandas as pd
from NiChart.core.dataio import DataIO
# import dtale
from NiChart.core.baseplugin import BasePlugin
from NiChart.core import iStagingLogger
from NiChart.core.gui.SearchableQComboBox import SearchableQComboBox
from NiChart.core.gui.CheckableQComboBox import CheckableQComboBox
from NiChart.core.gui.NestedQMenu import NestedQMenu
from NiChart.core.model.datamodel import PandasModel

logger = iStagingLogger.get_logger(__name__)

class NormalizeView(QtWidgets.QWidget,BasePlugin):

    def __init__(self):
        super(NormalizeView,self).__init__()
        
        self.data_model_arr = None
        self.active_index = -1
        
        self.cmds = None        

        root = os.path.dirname(__file__)
        self.readAdditionalInformation(root)
        self.ui = uic.loadUi(os.path.join(root, 'normalizeview.ui'),self)
        
        ## Main view panel        
        self.mdi = self.findChild(QMdiArea, 'mdiArea')       
        self.mdi.setBackground(QtGui.QColor(245,245,245,255))
                
        ## Panel for Divide By
        self.ui.comboBoxDivideByCat = QComboBox(self.ui)
        self.ui.comboBoxDivideByCat.setEditable(False)
        self.ui.vlComboDivideBy.addWidget(self.ui.comboBoxDivideByCat)

        self.ui.comboBoxDivideByVar = QComboBox(self.ui)
        self.ui.comboBoxDivideByVar.setEditable(False)
        self.ui.vlComboDivideBy.addWidget(self.ui.comboBoxDivideByVar)

        ## Panel for Apply To
        self.ui.comboBoxSelCat = CheckableQComboBox(self.ui)
        self.ui.comboBoxSelCat.setEditable(False)
        self.ui.vlComboSel.addWidget(self.ui.comboBoxSelCat)

        self.ui.comboBoxSelVar = CheckableQComboBox(self.ui)
        self.ui.comboBoxSelVar.setEditable(False)
        self.ui.vlComboSel.addWidget(self.ui.comboBoxSelVar)

        ## Options panel is not shown if there is no dataset loaded
        self.ui.wOptions.hide()
        
        self.ui.edit_activeDset.setReadOnly(True)
        
        self.ui.wOptions.setMaximumWidth(300)
        

    def SetupConnections(self):
        
        self.data_model_arr.active_dset_changed.connect(self.OnDataChanged)
        
        self.ui.normalizeBtn.clicked.connect(self.OnNormalizeBtnClicked)

        self.ui.comboBoxSelCat.view().pressed.connect(self.OnApplyToCatSelected)

        self.ui.comboBoxDivideByCat.currentIndexChanged.connect(self.OnDivideByCatChanged)

        ## https://gist.github.com/ales-erjavec/7624dd1d183dfbfb3354600b285abb94

    def OnApplyToCatSelected(self, index):
        
        selItem = self.ui.comboBoxSelCat.model().itemFromIndex(index) 
        
        ## Read selected cat value
        selCat = selItem.text()

        ## Get list of cat to var name mapping
        dmap = self.data_model_arr.datasets[self.active_index].data_cat_map
        
        ## Check status of edit box for sel category
        isChecked = selItem.checkState()
        
        ## Set/reset check mark for selected var names in combobox for variables
        ## Update sel cat check box
        checkedVars = dmap.loc[[selCat]].VarName.tolist()
        if selItem.checkState() == QtCore.Qt.Checked: 
            self.ui.comboBoxSelVar.uncheckItems(checkedVars)      ## Selected vars are set to "checked"
            selItem.setCheckState(QtCore.Qt.Unchecked)
        else:
            self.ui.comboBoxSelVar.checkItems(checkedVars)      ## Selected vars are set to "checked"
            selItem.setCheckState(QtCore.Qt.Checked)
        
        #logger.info(checkedVars)


    def OnDivideByCatChanged(self):
        selCat = self.ui.comboBoxDivideByCat.currentText()
        tmpData = self.data_model_arr.datasets[self.active_index]
        
        selVars = tmpData.data_cat_map.loc[[selCat]].VarName.tolist()
        self.PopulateComboBox(self.ui.comboBoxDivideByVar, selVars)

    def PopulateTable(self, data):
        
        ### FIXME : Data is truncated to single precision for the display
        ### Add an option in settings to let the user change this
        data = data.round(1)

        model = PandasModel(data)
        self.dataView = QtWidgets.QTableView()
        self.dataView.setModel(model)

    #add the values to comboBox
    def PopulateComboBox(self, cbox, values, strPlaceholder = None, bypassCheckable=False):
        cbox.blockSignals(True)
        cbox.clear()

        if bypassCheckable:
            cbox.addItemsNotCheckable(values)  ## The checkableqcombo for var categories
                                               ##   should not be checkable
        else:
            cbox.addItems(values)
            
        if strPlaceholder is not None:
            cbox.setCurrentIndex(-1)
            cbox.setEditable(True)
            cbox.setCurrentText(strPlaceholder)
        cbox.blockSignals(False)

    def OnDataChanged(self):
        
        if self.data_model_arr.active_index >= 0:
     
            ## Make options panel visible
            self.ui.wOptions.show()
        
            ## Set fields for various options     
            self.active_index = self.data_model_arr.active_index
                
            ## Get data variables
            dataset = self.data_model_arr.datasets[self.active_index]
            colNames = dataset.data.columns.tolist()
            catNames = dataset.data_cat_map.index.unique().tolist()

            logger.info(self.active_index)
            logger.info(catNames)
            
            ## Set active dset name
            self.ui.edit_activeDset.setText(self.data_model_arr.dataset_names[self.active_index])

            ## Update selection, sorting and drop duplicates panels
            self.UpdatePanels(catNames, colNames)

    def UpdatePanels(self, catNames, colNames):
        
        if len(catNames) == 1:      ## Single variable category, no need for category combobox
            self.ui.comboBoxDivideByCat.hide()
            self.ui.comboBoxSelCat.hide()
        else:
            self.ui.comboBoxDivideByCat.show()
            self.ui.comboBoxSelCat.show()
            self.PopulateComboBox(self.ui.comboBoxDivideByCat, catNames, '--var group--')
            self.PopulateComboBox(self.ui.comboBoxSelCat, catNames, '--var group--')
        self.PopulateComboBox(self.ui.comboBoxDivideByVar, colNames, '--var name--')
        self.PopulateComboBox(self.ui.comboBoxSelVar, colNames, '--var name--')
    
    
    def AddNewVarsToDict(self, newVars, outCat='NormalizeView'):

        ## Create dict with info about new columns
        dfCols = ['VarName', 'VarDesc', 'VarCat', 'SourceDict']
        dfDict = pd.DataFrame(index = newVars, columns = dfCols)
        dfDict.index.name = 'Var'
        dfDict['VarName'] = newVars
        dfDict['VarDesc'] = 'Generated in NiChart NormalizeView'
        #dfDict['VarDesc'] = dfDict.VarDesc.apply(lambda x: [x])
        dfDict['VarCat'] = outCat
        dfDict['VarCat'] = dfDict.VarCat.apply(lambda x: [x])
        dfDict['SourceDict'] = 'NiChart_NormalizeView'
        
        ## Update data dictionary
        self.data_model_arr.AddDataDict(dfDict)
        
    ## Normalize data by the given variable
    def NormalizeData(self, df, selVars, normVar, outSuff):
        dfNorm = 100 * df[selVars].div(df[normVar], axis=0)
        dfNorm = dfNorm.add_suffix('_' + outSuff)
        newVars = dfNorm.columns.tolist()
        dfOut = pd.concat([df, dfNorm], axis=1)        
        return dfOut, newVars
    
    def OnNormalizeBtnClicked(self):
        
        ## Read normalize options
        dset_name = self.data_model_arr.dataset_names[self.active_index]        

        normVar = self.ui.comboBoxDivideByVar.currentText()
        str_normVar = ','.join('"{0}"'.format(x) for x in [normVar])
        
        selVars = self.ui.comboBoxSelVar.listCheckedItems()
        str_selVars = ','.join('"{0}"'.format(x) for x in selVars)
        
        outSuff = self.ui.edit_outSuff.text()
        if outSuff[0] == '_':
            outSuff = 'NORM'
        if outSuff[0] == '_':
            outSuff = outSuff[1:]
        outCat = outSuff

        # Get active dset, apply normalization
        dfCurr = self.data_model_arr.datasets[self.active_index].data
        dfNorm, newVars = self.NormalizeData(dfCurr, selVars, normVar, outSuff)

        # Set updated dset
        self.data_model_arr.datasets[self.active_index].data = dfNorm
        
        ## Create dict with info about new columns
        self.AddNewVarsToDict(newVars, outCat = outCat)
            
        ## Call signal for change in data
        self.data_model_arr.OnDataChanged()
        
        ## Load data to data view (reduce data size to make the app run faster)
        ##   This view shows only the out variables
        tmpData = self.data_model_arr.datasets[self.active_index].data
        tmpData = tmpData[newVars]
        tmpData = tmpData.head(self.data_model_arr.TABLE_MAXROWS)
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
        cmds.append('# Normalize dataset')
        cmds.append('dfNorm = 100 * ' + dset_name + '[[' + str_selVars + ']].div(' + dset_name + '["' + normVar + '"], axis=0)')
        cmds.append('outSuff = "' + outSuff + '"')
        cmds.append('dfNorm = dfNorm.add_suffix("_" + outSuff)')
        cmds.append(dset_name + ' = pd.concat([' + dset_name + ', dfNorm], axis=1)')
        cmds.append(dset_name + '.head()')
        cmds.append('')        
        self.cmds.add_cmd(cmds)
        ##-------
   
    
