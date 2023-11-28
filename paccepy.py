#!/usr/bin/python
import os, glob
from pylab import *
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from scipy import interpolate
from scipy import integrate
from  scipy import ndimage
import re
import time

from PacceFunctions import ComputEW as pacce

formf='{:5.2F}'
#IndexDefs=['config1','config2','config3','config']
IndexDefs=['Elham_pacce_Defs.ind']#,'config2']
#galList=['MeanSpec2.txt',]
#galList=glob.glob('*.txt')
g=open('lista.lis')

#g=open('galaxies_short.txt')

galList=[]
tmp=g.readlines()
for f in tmp:
    x=re.sub('\n','',f)
    gl=glob.glob(x)
    galList=append(galList,gl)

for rr in range(0,len(IndexDefs),1):
    out='FinalOpticalMeasurements.txt'
    save=open(out,'w+')
#    save.write(r'\documentclass[5pt]{article}')
#    save.write('\n')
#    save.write(r'\usepackage[dvips]{epsfig}')
#    save.write('\n')
#    save.write(r'\usepackage[dvips]{graphics}')
#    save.write('\n')
#    save.write(r'\usepackage{longtable}')
#    save.write('\n')
#    save.write(r'\usepackage{lscape}')
#    save.write('\n')
#    save.write(r'\begin{document}')
#    save.write('\n')
#    save.write(r'\begin{tiny}')
#    save.write('\n')
#    save.write(r'\renewcommand{\tabcolsep}{0.70mm}')
#    save.write('\n')    
#    save.write(r'\begin{landscape}')
#    save.write('\n')
#    save.write(r'\begin{longtable}{llccccccccccccccccccccc}')
#    save.write('\n')
#    save.write(r'\hline')
#    save.write('\n')
#    save.write('Galaxy / Line')
    print("Meassuring with definitions of: "+IndexDefs[rr])
    (line,mens)=pacce(galList[0],IndexDefs[rr],Doplots=True,simulate=False,SimTimes=100)
    save.write('Galaxy')
    for l in line:
            save.write('   '+l+'  e_'+l)#+'  '+str(formf.format(mens[i][0])) +'  '+ str(formf.format(mens[i][1]))+'  '+str(formf.format(mens[i][2]))+'  '+str(formf.format(mens[i]
#    save.write('\\\\')
    for galname in galList:
        print("Doing File="+galname)
        (line,mens)=pacce(galname,IndexDefs[rr],Doplots=True,simulate=False,SimTimes=100)
        i=0
        save.write('\n'+re.split('_',galname)[0])
        for l in line:
            if mens[i][0] <= 0:
               ew=formf.format(0.0)
               sigew=formf.format(0.0)
               mid='  '
               sn='    '
            if mens[i][0] > 0:
               ew=str(formf.format(mens[i][0]))
               sigew=str(formf.format(mens[i][1]))
               mid='  '
               sn=str(formf.format(mens[i][2]))
            save.write('    '+ew +mid+sigew)
            i=i+1
#        save.write('\\\\')
#    save.write('\n')
#    save.write(r'\hline')
#    save.write('\n')
#    save.write(r'\end{longtable}')
#    save.write('\n')
#    save.write(r'\end{landscape}')
#    save.write('\n')
#    save.write(r'\end{tiny}')
#    save.write('\n')
#    save.write(r'\end{document}')
   
    save.close()
    lin=np.loadtxt(out,dtype='str')
    np.savetxt(re.sub('.txt','_FMT.txt',out),lin,fmt='%12s')
#os.system('latex '+out)
#os.system('dvipdf '+re.sub('.tex','.dvi',out))

