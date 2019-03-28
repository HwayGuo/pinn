# ______          _           _     _ _ _     _   _      
# | ___ \        | |         | |   (_) (_)   | | (_)     
# | |_/ / __ ___ | |__   __ _| |__  _| |_ ___| |_ _  ___ 
# |  __/ '__/ _ \| '_ \ / _` | '_ \| | | / __| __| |/ __|
# | |  | | | (_) | |_) | (_| | |_) | | | \__ \ |_| | (__ 
# \_|  |_|  \___/|_.__/ \__,_|_.__/|_|_|_|___/\__|_|\___|
# ___  ___          _                 _                  
# |  \/  |         | |               (_)                 
# | .  . | ___  ___| |__   __ _ _ __  _  ___ ___         
# | |\/| |/ _ \/ __| '_ \ / _` | '_ \| |/ __/ __|        
# | |  | |  __/ (__| | | | (_| | | | | | (__\__ \        
# \_|  |_/\___|\___|_| |_|\__,_|_| |_|_|\___|___/        
#  _           _                     _                   
# | |         | |                   | |                  
# | |     __ _| |__   ___  _ __ __ _| |_ ___  _ __ _   _ 
# | |    / _` | '_ \ / _ \| '__/ _` | __/ _ \| '__| | | |
# | |___| (_| | |_) | (_) | | | (_| | || (_) | |  | |_| |
# \_____/\__,_|_.__/ \___/|_|  \__,_|\__\___/|_|   \__, |
#                                                   __/ |
#                                                  |___/ 
#														  
# MIT License
# 
# Copyright (c) 2019 Probabilistic Mechanics Laboratory
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================
""" Mechanical propagation sample 
"""
import numpy as np
import pandas as pd
import tensorflow as tf

import matplotlib.pyplot as plt

from tensorflow.python.framework import ops

from model import create_model
from tqdm import tqdm
# =============================================================================
# auxiliary functions
# =============================================================================
def sncurve(Seq,a,b):
    da = 1/10**(a*Seq+b)
    return da

def walker(dS,F,R,beta,gamma,Co,m,a):
    dk = F*dS*np.sqrt(np.pi*a)    
    sig = 1/(1+np.exp(beta*R))
    gammav = sig*gamma
    C = Co/((1-R)**(m*(1-gammav)))    
    da = C*(dk**m)
    return da

def sigmoid(dai,dap,a,alpha,ath):
    m = 1/(1+np.exp(-alpha*(a-ath)))
    da = m*dap+(1-m)*dai
    return da
# =============================================================================
# Main
# =============================================================================
#--------------------------------------------------------------------------
if __name__ == "__main__":
    myDtype = tf.float32  # defining type for the layer
    
    dfSeq = pd.read_csv('Equiv_stress.csv', index_col = None) # Equivalent stress data
    Seq = dfSeq.values[:,1:4] # Equivalent stress history for all machines
    Seq = Seq.transpose() # setting axis as [# of machines, # of cycles]
    dfdS = pd.read_csv('Delta_load.csv', index_col = None) # Load data
    dS = dfdS.values[:,1:4] # loads history for all machines 
    dS = dS.transpose()
    dfR = pd.read_csv('Stress_ratio.csv', index_col = None) # Stress ratio data
    R = dfR.values[:,1:4] # stress ratio values for all machines
    R = R.transpose()
    dfa = pd.read_csv('Crack_length.csv', index_col = None) # crack length data
    cr = dfa.values[:,1:4] # crack length values for all machines
    cr = cr.transpose()
    
    nFleet, nCycles  = np.shape(cr) 
    
    # RNN inputs
    input_array = np.dstack((Seq, dS))
    input_array = np.dstack((input_array, R))
    inputTensor = ops.convert_to_tensor(input_array, dtype = myDtype)
    
    a0RNN = np.zeros((input_array.shape[0], 1)) 
    a0RNN[0] = cr[0,0] # initial crack length asset #1
    a0RNN[1] = cr[1,0] # initial crack length asset #2
    a0RNN[-1] = cr[-1,0] # initial crack length asset #3
    a0RNN = ops.convert_to_tensor(a0RNN, dtype=myDtype)
    
    # model parameters
    a,b = -3.73,13.48261 # Sn curve coefficients 
    F = 2.8 # stress intensity factor
    beta,gamma = -1e8,.68 # Walker model customized sigmoid function parameters
    Co,m = 1.1323e-10,3.859 # Walker model coefficients (similar to Paris law)
    alpha,ath = 1e8,.5e-3 # sigmoid selector parameters
    #--------------------------------------------------------------------------
    batch_input_shape = input_array.shape
    
    selectsn = [1]
    selectdK = [0,2]
    selectprop = [3]
    selectsig = [0]
    
    model = create_model(a, b, F, beta, gamma, Co, m , alpha, ath, a0RNN, batch_input_shape, selectsn, selectdK, selectprop, selectsig, myDtype, return_sequences = True)
    results = model.predict_on_batch(input_array) # custumized layer prediction
    # =============================================================================
    # Numpy function     
    # =============================================================================
    dai = np.zeros((nFleet,nCycles))
    dap = np.zeros((nFleet,nCycles))
    da = np.zeros((nFleet,nCycles))
    an = np.zeros((nFleet,nCycles))
    print('Numpy results replication:')
    for ii in tqdm(range(nFleet)):
        aux = 0
        for jj in range(nCycles):
            dai[ii,jj] = sncurve(Seq[ii,jj],a,b)
            dap[ii,jj] = walker(dS[ii,jj],F,R[ii,jj],beta,gamma,Co,m,aux)
            da[ii,jj] = sigmoid(dai[ii,jj],dap[ii,jj],aux,alpha,ath)
            aux+=da[ii,jj]
            an[ii,jj] = aux
        
    #--------------------------------------------------------------------------
    fig  = plt.figure(1)
    fig.clf()
    
    plt.plot(1e3*cr[0,:],':k', label = 'asset #1')
    plt.plot(1e3*cr[1,:],'--m', label = 'asset #2')
    plt.plot(1e3*cr[-1,:],'-g', label = 'asset #3')
    plt.plot(1e3*an[0,:],'-', label = 'numpy #1')
    plt.plot(1e3*an[0,:],':', label = 'numpy #2')
    plt.plot(1e3*an[0,:],':', label = 'numpy #3')
    plt.plot(1e3*results[0,:,0],':', label = 'PINN #1')
    plt.plot(1e3*results[1,:,0],'--', label = 'PINN #2')
    plt.plot(1e3*results[-1,:,0],'-', label = 'PINN #3')
    
    
    plt.title('Crack Init. and Prop.')
    plt.xlabel('Cycles')
    plt.ylabel(' crack length [mm]')
    plt.legend(loc=0, facecolor = 'w')
    plt.grid(which = 'both')
    