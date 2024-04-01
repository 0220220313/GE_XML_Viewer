#!/usr/bin/env python
# coding: utf-8

# In[1]:


# coding: utf-8
import os
import sys
import csv
import base64
import xmltodict
import numpy as np
from glob import glob
import matplotlib.pyplot as plt


# In[2]:


from PySide6 import QtWidgets,QtCore,QtGui
from PySide6.QtWidgets import *


# In[3]:


import PIL
from PIL import Image, ImageQt


# In[4]:



ECG_FIELD_NAMES = [
    'I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'
]
ECG_FIELD_DICT = dict(zip(ECG_FIELD_NAMES , np.arange(len(ECG_FIELD_NAMES))))
def check_xml(the_path) :
    with open(the_path, encoding='utf-8') as f:
        x = f.read()
    try:
        xd = xmltodict.parse(x)
        return xd
    except:
        print('Error loading XML')
        return None
def read_xml(xd):
    wavedata = [list() for _ in range(len(ECG_FIELD_NAMES))]
    try:
        leads_data = xd['RestingECG']['Waveform'][1]['LeadData']
    except:
        leads_data = xd['RestingECG']['Waveform']['LeadData']
    for w in leads_data: 
        lead_ID =ECG_FIELD_DICT[w['LeadID']]
        wavedata[lead_ID] = np.frombuffer(base64.b64decode(w['WaveFormData']), 
                                              dtype=np.int16)*(float(w['LeadAmplitudeUnitsPerBit'])/1000)
    wavedata[ECG_FIELD_DICT["III"]] = wavedata[ECG_FIELD_DICT["II"]] - wavedata[ECG_FIELD_DICT["I"]]
    wavedata[ECG_FIELD_DICT["aVR"]] = -1*((wavedata[ECG_FIELD_DICT["I"]] + wavedata[ECG_FIELD_DICT["II"]])/2)
    wavedata[ECG_FIELD_DICT["aVL"]] = wavedata[ECG_FIELD_DICT[ "I"]] - wavedata[ECG_FIELD_DICT["II"]]/2
    wavedata[ECG_FIELD_DICT["aVF"]] = wavedata[ECG_FIELD_DICT["II"]] - wavedata[ECG_FIELD_DICT[ "I"]]/2 
    return np.array(wavedata)
def get_info(xd) :
    try : 
        patid = xd['RestingECG']['PatientDemographics']['PatientID']
        age = xd['RestingECG']['PatientDemographics']['PatientAge']
        gender = xd['RestingECG']['PatientDemographics']['Gender']
        accno = xd['RestingECG']['TestDemographics']['SecondaryID']
        name = xd['RestingECG']['PatientDemographics']['PatientLastName']
        loc = xd['RestingECG']['TestDemographics']['LocationName']
        studydate = '/'.join([xd['RestingECG']['TestDemographics']
                                     ['AcquisitionDate'].split('-')[i] for i in [2, 0, 1]])
        studytime = ':'.join(
            xd['RestingECG']['TestDemographics']['AcquisitionTime'].split(':'))
        studytime = studydate+' '+studytime
        return [True ,  patid, accno, name, gender, age, studytime, loc]
    except:
        return [False ] + [None for _ in range(7)]


# In[5]:


def plot_ekg(ecg_npy):
    # X_INCH = 7
    # Y_INCH = 11
    X_MM = 268
    Y_MM = 129
    M_X_INCH = float(X_MM) / 25.4
    M_Y_INCH = float(Y_MM) / 25.4
    THIN_WIDTH = 0.04
    FAT_WIDTH = 0.2

    f = plt.figure(figsize=(M_X_INCH,M_Y_INCH), dpi=150)  # 英寸

    axes = f.add_axes( (0, 0, 1, 1), frame_on=False )
    axes.set_xlim(-0.5, X_MM-0.5)     # 毫米
    axes.set_ylim(-0.5, Y_MM-0.5)    
    def get_line_width(i):
        if i % 5 == 0 :
            return FAT_WIDTH 
        else:
            return THIN_WIDTH
    for i in range(0, X_MM):
        if i == (X_MM-1):
            axes.axvline(x=i,linewidth=FAT_WIDTH,color='red') # Last tick is fat line
        else:
            axes.axvline(x=i,linewidth=get_line_width(i),color='red') # every 5th line is fat line
    for i in range(0, Y_MM):
        if i == (Y_MM-1):
            axes.axhline(y=i,linewidth=FAT_WIDTH,color='red')
        else:
            axes.axhline(y=i,linewidth=get_line_width(i),color='red')
    axes.set_xticks([])
    axes.set_yticks([])
    
    ecg_offset = 0
    h_offset_list = [6,68,132,194]
    v_offset_list = [115, 82, 48]
    for i , (single_ecg, lead_name) in enumerate(zip(ecg_npy,ECG_FIELD_NAMES)) :
        if i%4==0 :
            ecg_offset += 1
        h_offset = h_offset_list[int(i//3)]
        v_offset = v_offset_list[int(i %3)]
        plt.plot((np.arange(1230)*0.05+h_offset),single_ecg[1250*(ecg_offset-1):1250*ecg_offset-20]*10+v_offset, color='black', linewidth=0.5)
        plt.text(h_offset,v_offset-3,lead_name,horizontalalignment='left',verticalalignment='top', fontsize=18)
    
    
    h_offset,v_offset = 6, 13
    plt.plot((np.arange(5000)*0.05+h_offset),ecg_npy[1]*10+v_offset, color='black', linewidth=0.5)
    plt.text(h_offset,v_offset-3,"II",horizontalalignment='left',verticalalignment='top', fontsize=18)
    f.canvas.draw()
    ecg_image = PIL.Image.frombytes('RGBA',f.canvas.get_width_height(),f.canvas.tostring_argb())
    plt.clf()
    del f
    ecg_image = np.array(ecg_image)    
    ecg_image = ecg_image[...,[1,2,3,0]]
    ecg_image = Image.fromarray(ecg_image) 
    return ecg_image


# In[6]:


def package_widget(widget, parent, Geometry , text = None , font = QtGui.QFont("Times", 25 )) :
    Geometry = list(Geometry)
    tmp_label = QLabel(parent)
    tmp_label.setFrameStyle(QFrame.Box | QFrame.Plain)
    tmp_label.setLineWidth(1)
    tmp_label.setGeometry(*Geometry)  
    if widget == QLabel :
        new_widget = tmp_label
    else :
        new_widget = widget(tmp_label)
        Geometry = [0,0] + Geometry[2:]
        new_widget.setGeometry(*Geometry)  
    if text is not None  :
        new_widget.setText(text)
    if font is not None  :
        new_widget.setFont(font)  
    return new_widget
def process_diagnosis(raw_diagnosis) :
    diagnosis = []
    if type(raw_diagnosis)==dict :
        raw_diagnosis=[raw_diagnosis]
    Flag = False
    for s in raw_diagnosis :
        if Flag :
            diagnosis[-1]+=' '+s['StmtText']
        else :
            diagnosis.append(s['StmtText'])
        if 'StmtFlag' not in s.keys() :
            Flag = True
        elif s['StmtFlag']== 'ENDSLINE':
            Flag = False
        else :
            diagnosis.append('There have some error diagnosis cannot be extracted')
    return diagnosis

class WranDialog(QtWidgets.QMessageBox): 
    def __init__(self, text, parent=None): 
        QtWidgets.QMessageBox.__init__(self, parent) 
        self.setWindowTitle('Warnning')
        self.setText(f'\n\n{text:^50}.\n\n')
        self.exec()


# In[8]:


class MainWindow(QMainWindow):
    def __init__(self):
        # Window
        super(MainWindow, self).__init__()
        self.resize(1920, 1080)
        self.setWindowTitle("ECG XML Viewer")
        self.folderpath = None
        self.file_path = None
        self.load_csv()
    ## QLabel
        self.left_label = QLabel(self)
        self.left_label.setFrameStyle(QFrame.WinPanel | QFrame.Plain)
        self.left_label.setLineWidth(2)
        self.left_label.setGeometry(0, 0, 1600, 780)
        self.right_label = QLabel(self)
        self.right_label.setFrameStyle(QFrame.WinPanel | QFrame.Plain)
        self.right_label.setLineWidth(2)
        self.right_label.setGeometry(1600, 0, 320, 1080)   
        self.buttom_label = QLabel(self)
        self.buttom_label.setFrameStyle(QFrame.WinPanel | QFrame.Plain)
        self.buttom_label.setLineWidth(2)
        self.buttom_label.setGeometry(0, 780, 1600, 300)
        
    ## Buttons
        self.B_select_file = package_widget(QPushButton, self.right_label ,(0, 0, 320, 100), 'Select ECG XML Folder',QtGui.QFont("Times", 15 ))
        self.B_select_file.clicked.connect(self.select_file)
        self.B_save_note = package_widget(QPushButton, self.right_label ,(0, 980, 320, 40),'Save Note')
        self.B_save_note.clicked.connect(self.save_note)
            
    ## TextLabel
        ## Right
        self.folder_path_label = package_widget(QLabel, self.right_label, (0, 100, 320, 40),
                                               text = 'Please Select ECG XML Folder First',
                                               font = None)
        self.note_title = package_widget(QLabel, self.right_label, (0, 640, 320, 50) ,text = 'Note')
        self.note_label = package_widget(QTextEdit, self.right_label, (0, 690, 320, 290)  ,text = '無')
        ## Buttom
        self.diagnosis_title = package_widget(QLabel, self.buttom_label, (800, 0, 800, 60), text = 'ECG Diagnosis')
        self.diagnosis_label = package_widget(QTextBrowser, self.buttom_label, (800, 60, 800, 180), font = QtGui.QFont("Times", 20 ))
        self.patient_tags = [
            package_widget(QLabel, self.buttom_label, (  0,  0, 100, 60), text = '   病歷號', font = QtGui.QFont("Times", 15 )),
            package_widget(QLabel, self.buttom_label, (400,  0, 100, 60), text = '   表單號', font = QtGui.QFont("Times", 15 )),
            package_widget(QLabel, self.buttom_label, (  0, 60, 100, 60), text = '     姓名', font = QtGui.QFont("Times", 15 )),
            package_widget(QLabel, self.buttom_label, (400, 60, 100, 60), text = '     性別', font = QtGui.QFont("Times", 15 )),
            package_widget(QLabel, self.buttom_label, (600, 60, 100, 60), text = '     年紀', font = QtGui.QFont("Times", 15 )),
            package_widget(QLabel, self.buttom_label, (  0,120, 100, 60), text = ' 施作時間', font = QtGui.QFont("Times", 15 )),
            package_widget(QLabel, self.buttom_label, (400,120, 100, 60), text = ' 施作地點', font = QtGui.QFont("Times", 15 )),
            package_widget(QLabel, self.buttom_label, (  0,180, 100, 60), text = ' 檔案路徑', font = QtGui.QFont("Times", 15 )),
            
        ]
        self.patient_infos = [
            package_widget(QTextBrowser, self.buttom_label, (100,  0, 300, 60), font = QtGui.QFont("Times", 15 )),
            package_widget(QTextBrowser, self.buttom_label, (500,  0, 300, 60), font = QtGui.QFont("Times", 15 )),
            package_widget(QTextBrowser, self.buttom_label, (100, 60, 300, 60), font = QtGui.QFont("Times", 15 )),
            package_widget(QTextBrowser, self.buttom_label, (500, 60, 100, 60), font = QtGui.QFont("Times", 15 )),
            package_widget(QTextBrowser, self.buttom_label, (700, 60, 100, 60), font = QtGui.QFont("Times", 15 )),
            package_widget(QTextBrowser, self.buttom_label, (100,120, 300, 60), font = QtGui.QFont("Times", 15 )),
            package_widget(QTextBrowser, self.buttom_label, (500,120, 300, 60), font = QtGui.QFont("Times", 15 )),
            package_widget(QTextBrowser, self.buttom_label, (100,180, 700, 60), font = QtGui.QFont("Times", 15 )),
            
        ]
        
    
    ## ListLabel
        self.file_list_dialog = package_widget(QListWidget, self.right_label ,(0, 140, 320, 500), font = None)
        self.file_list_dialog.itemClicked.connect(self.FileClicked)
        
    ## Image Plot
        self.img_label = QLabel(self.left_label)
        self.img_label.setGeometry(10, 10, 1580, 760)
    def load_csv(self) :
        if os.path.exists('ECG_info.csv') :
            with open('ECG_info.csv', newline='') as csvfile:
                rows = csv.reader(csvfile)
                self.csv_data = [row for row in rows]
                self.csv_data = self.csv_data[1:]
                self.idx_dict  = dict(zip([the_data[-2] for the_data in self.csv_data] , np.arange(len(self.csv_data)).astype(int) ))
        else :
            self.csv_data = []
            self.idx_dict = {}
    def processed_xml(self) :
        xd = check_xml(self.file_path)
        self.drow_ecg(xd)
        raw_diagnosis = xd['RestingECG']['OriginalDiagnosis']['DiagnosisStatement']
        diagnosis = '\n'.join(process_diagnosis(raw_diagnosis))
        self.diagnosis_label.setText(diagnosis)
        patient_info = get_info(xd)[1:]
        patient_info += [self.file_path]
        _ = [the_text.setText(str(_info)) for _info, the_text in zip(patient_info,self.patient_infos)]
        _ = [the_weidget.setAlignment(QtCore.Qt.AlignRight) for the_weidget in  self.patient_infos]
        
        if self.file_path not in self.idx_dict.keys() :
            self.csv_data.append(patient_info+['無'])
            self.idx_dict[self.file_path] = len(self.csv_data)-1
        self.note_label.setText(self.csv_data[self.idx_dict[self.file_path]][-1])
        
    def drow_ecg(self , xd):
        ecg_npy = read_xml(xd)
        ecg_image = plot_ekg(ecg_npy)
        ecg_image = ImageQt.ImageQt(ecg_image)
        ecg_image = QtGui.QPixmap.fromImage(ecg_image)
        self.img_label.setPixmap(ecg_image)
        self.img_label.setScaledContents(True)
        
    def select_file(self, event) :
        folderpath = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folderpath is None or len(glob(f'{folderpath}/*.xml'))==0  :
            WranDialog('Folder not select or no xml in folder')
            return 

        self.folderpath = folderpath
        self.folder_path_label.setText(f'current path :\n {self.folderpath:>80}')
        file_paths = glob(f'{self.folderpath}/*.xml') 
        file_paths = [p.replace(self.folderpath,'') for p in file_paths]
        self.file_list_dialog.clear()
        self.file_paths_item = [QListWidgetItem( self.file_list_dialog) for _ in range(len(file_paths))]
        for fp, item in zip(file_paths, self.file_paths_item) :
            item.setText(fp)
            if f'{self.folderpath}{fp}' in self.idx_dict :
                item.setBackground(QtGui.QColor("LightGray"))
            
        self.FileClicked(self.file_paths_item[0])
        
            
    
    
    
    def FileClicked(self,item) :
        if self.file_path is not None :
            self.save_note()
        self.file_path = f'{self.folderpath}{item.text()}'
        item.setBackground(QtGui.QColor("LightGray"))
        print(self.file_path)
        self.processed_xml()     
        
    def save_note(self) :
        note_str = self.note_label.toPlainText()
        self.csv_data[self.idx_dict[self.file_path]][-1] = note_str
    def closeEvent(self, event):
        with open('ECG_info.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['病例號', '表單號', '姓名', '性別', '年紀', '施作時間', '施作地點', '檔案路徑', '備註'])
            for row in self.csv_data :
                writer.writerow(row)
            
        event.accept() 
            
if __name__ == "__main__":
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


# In[ ]:




