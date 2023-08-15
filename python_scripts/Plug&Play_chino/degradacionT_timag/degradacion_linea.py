import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from scipy import signal
from matplotlib import pyplot as plt
from PIL import Image


#funcion que toma como entrada el armonico a sintonizar y las dimensiones de la imagen a espiar y devuelve un array con taps de g(t)
def g_taps(dim_vertical, dim_horizontal, armonico):

    #defino variables iniciales
    f_p = dim_vertical * dim_horizontal * 60
    f_sdr = 50e6
    harm = armonico * f_p
    
    #para el correcto funcionamiento: dependiendo del armonico, elijo cuantas muestras por pulso
    if (armonico < 5 ):
        muestras_por_pulso  = 5
    else:
        muestras_por_pulso  = 20

    samp_rate = muestras_por_pulso * f_p
    H_samples = dim_horizontal * muestras_por_pulso

    #creo el pulso
    t_continuous = np.linspace(start = 0, stop = H_samples/samp_rate, num = H_samples, endpoint= False)
    pulso = np.zeros(H_samples)
    pulso[:muestras_por_pulso] = 1

    #traslado el espectro del pulso el armonico correspondiente
    frec_armonico = np.exp(-2j*np.pi*harm*t_continuous)
    pulso_complejo = pulso*frec_armonico

    #creo el lpf del sdr
    b, a = signal.butter(6, f_sdr/2, fs=samp_rate, btype='lowpass', analog=False)

    #filtro con lpf el pulso multiplicado por armonico. El resultado es g
    g_t = signal.lfilter(b, a, pulso_complejo)
    #g_t = signal.decimate(g_t,q = muestras_por_pulso)

    # si armonico crece, necesito mas taps
    if (armonico < 5):
        g_t = g_t[:61]
    else:
        g_t = g_t[:300]

    g_t_max = np.max(np.abs(g_t))
 
    g_t = g_t / g_t_max

    return torch.tensor(g_t,dtype = torch.complex64).reshape(1,1,len(g_t))
    
def forward(dim_filas, dim_columnas, img_linea, armonico = 3):
    #paso img a complex
    img_linea_complex = img_linea.to(torch.complex64)
    #img_fila = img_linea_complex.reshape(1, 1, dim_filas * dim_columnas)
    img_fila = img_linea_complex.unsqueeze(0).unsqueeze(0)
    g_t = g_taps(dim_filas, dim_columnas, armonico)
    #size_g_t = g_t.numel()
    img_fila_salida = nn.functional.conv1d(img_fila, g_t, stride = 1, padding = 'same', bias = None)[0,0,:]#.reshape((filas,columnas))
    img_fila_out = img_fila_salida.abs()
    img_fila_norm = (img_fila_out - img_fila_out.min())/(img_fila_out.max() - img_fila_out.min())
    #paso img_fila_salida a float
    return img_fila_norm.to(torch.float64)
    
