# -*- coding: utf-8 -*-
"""
Created on Tue Sep 27 13:13:34 2016

@author: Yang
5.7： 添加loss记录
5.6： 修改bug
5.5：调整drop out
5.2: 适用于欧氏距离的相似度输入
5.0: 依据之前的模型，建立新的模型，没有考虑max
3.4：去掉重复计算的变量,效率提高300%
3.3：前向计算返回parameter
3.2：添加minibath的外层循环，遮罩层
3.1:调整参数初始化的数值设置，对每个变量分配独自的rho权重
3.0:这一版本不包含gradient check,完成了minibatch
2.8:去掉之前构造的二次loss函数
2.7:添加minbatch
2.6:这一版本将求导功能写成函数
"""
import random
import numpy as np
import math
import copy

def sigmoid(x):
    return 1/(1+np.exp(-x))
#这里需要在每一步计算h之后对q和h_con做一下存储
def cal_q(parameter,i,j):
    h=parameter['h']
    s=parameter['s']
    if i==0 and j==0:
        h_l=np.zeros_like(h[0][0])
        h_d=np.zeros_like(h[0][0])
        h_t=np.zeros_like(h[0][0])
    elif i==0:
        h_l=np.zeros_like(h[0][0])
        h_d=np.zeros_like(h[0][0])
        h_t=h[i][j-1]
    elif j==0:
        h_l=h[i-1][j]
        h_d=np.zeros_like(h[0][0])
        h_t=np.zeros_like(h[0][0])
    else:
        h_t=h[i][j-1]
        h_l=h[i-1][j]
        h_d=h[i-1][j-1]
    h_con=np.concatenate((h_l,h_t,h_d),0)
    q=np.concatenate((h_l,h_t,h_d,s[i][j]),0)
    return h_con,q
#calculate reset gate from different directions
def cal_r(parameter,i,j):
    #只与前向有关
    q=parameter['q'][i][j]
    r=sigmoid(parameter['w_r'].dot(q)+parameter['b_r'])
    return r
    
#compute 'inner' update gate
def cal_z(parameter,i,j):
    #只与前向有关
    q=parameter['q'][i][j]
    z=sigmoid(parameter['w_z'].dot(q)+parameter['b_z'])
    return z

    
#def cal_z(parameter,i,j,w_z,b_z):
#    z=cal_z_pie(parameter,i,j,w_z,b_z)
#    return softmax(z)
# 
#compute hidden layer outout h
#在计算完h之后需要对产生的r，z，h'做存储，用于后向的导数计算
def cal_h(parameter,i,j):
    w=parameter['w']
    U=parameter['U']
    w_m=parameter['w_m']
    U_m=parameter['U_m']
    b=parameter['b']

    h=parameter['h'][i][j] 
    s=parameter['s'][i][j]    
    h_con=parameter['h_con'][i][j]
    

    z=cal_z(parameter,i,j)
    r=cal_r(parameter,i,j)
    
    ws=w.dot(s)
    h_pie=np.tanh(ws+U.dot(r*h_con)+b)    
    
    h=w_m.dot(z*h_con)+(U_m.dot(1-z))*h_pie+ws

        
    return h,h_pie,z,r

#后向传播计算导数 
'''checked and opted'''     
def delta_z(parameter,i,j):
    z_ij=parameter['z'][i][j]
    e_ij=parameter['e'][i][j]
    h_con_ij=parameter['h_con'][i][j]
    h_pie_ij=parameter['h_pie'][i][j]

    U_m=parameter['U_m']
    w_m=parameter['w_m']

    epsilon_z=(e_ij.T.dot(w_m)).T*h_con_ij-U_m.T.dot(e_ij*h_pie_ij)
    delta_z_val=epsilon_z*z_ij*(1-z_ij)
     
    return delta_z_val


#eq (1)
'''checked and opted'''
def delta_pie(parameter,i,j):
    z=parameter['z'][i][j]
    e=parameter['e'][i][j]
    h_pie_ij=parameter['h_pie'][i][j]

    U_m=parameter['U_m']

    delta_pie_val=e*(U_m.dot(1-z))*(1-h_pie_ij*h_pie_ij)
    return delta_pie_val

'''checked'''
def delta_r(parameter,i,j):
    '''chongfu'''
    '''只和前向计算有关，后向计算使用时可以直接调用'''
    #计算delta_pie,r
    U=parameter['U']
          
    h_con=parameter['h_con'][i][j]
    delta_pie_val=parameter['delta_pie'][i][j]
    
    
    epsilon_r=(delta_pie_val.T.dot(U)).T*h_con

    r_ij=parameter['r'][i][j]

    return epsilon_r*(r_ij*(1-r_ij))

#print (delta_r(parameter,1,1,'l'))
def epsilon(parameter,i,j,m,n):
    length=len(parameter['h'][0][0])


    w_m=parameter['w_m']
    w_r=parameter['w_r']
    w_z=parameter['w_z']
    e=parameter['e'];U=parameter['U']
    
    
    if i==m-1 and j==n-1:
        return parameter['w_s'].T
    elif i==m-1:
        
        firstline=(w_m.dot(parameter['z'][i][j+1]))*e[i][j+1]
        
        r_line=((parameter['delta_r'][i][j+1].T.dot(w_r)).T)[length:2*length]
        
        z_line=((parameter['delta_z'][i][j+1].T.dot(w_z)).T)[length:2*length]
    
        lastline=(((parameter['delta_pie'][i][j+1].T.dot(U)).T)*parameter['r'][i][j+1])[length:2*length]
        
        return lastline+r_line+z_line+firstline
    elif j==n-1:

        firstline=(w_m.dot(parameter['z'][i+1][j]))*e[i+1][j]

        r_line=((parameter['delta_r'][i+1][j].T.dot(w_r)).T)[:length]
        
        z_line=((parameter['delta_z'][i+1][j].T.dot(w_z)).T)[:length]
    
        lastline=(((parameter['delta_pie'][i+1][j].T.dot(U)).T)*parameter['r'][i+1][j])[:length]
        return lastline+r_line+z_line+firstline
    else:
        firstline=(w_m.dot(parameter['z'][i+1][j]))*e[i+1][j]+(w_m.dot(parameter['z'][i][j+1]))*e[i][j+1]+(w_m.dot(parameter['z'][i+1][j+1]))*e[i+1][j+1]
        r_line=((parameter['delta_r'][i+1][j].T.dot(w_r)).T)[:length]+((parameter['delta_r'][i][j+1].T.dot(w_r)).T)[length:2*length]+((parameter['delta_r'][i+1][j+1].T.dot(w_r)).T)[2*length:3*length]
        
        z_line=((parameter['delta_z'][i+1][j].T.dot(w_z)).T)[:length]+((parameter['delta_z'][i][j+1].T.dot(w_z)).T)[length:2*length]+((parameter['delta_z'][i+1][j+1].T.dot(w_z)).T)[2*length:3*length]
       
        lastline=(((parameter['delta_pie'][i+1][j].T.dot(U)).T)*parameter['r'][i+1][j])[:length]+(((parameter['delta_pie'][i][j+1].T.dot(U)).T)*parameter['r'][i][j+1])[length:2*length]+(((parameter['delta_pie'][i+1][j+1].T.dot(U)).T)*parameter['r'][i+1][j+1])[2*length:3*length]
        return lastline+r_line+z_line+firstline

def out(parameter):
    return parameter['w_s'].dot(parameter['h'][-1][-1])+parameter['b_s']

    
def forward(m,n,parameter,d_h):    
    for i in range(m):
        for j in range(n):
            parameter['h_con'][i][j],parameter['q'][i][j]=cal_q(parameter,i,j)
            parameter['h'][i][j],parameter['h_pie'][i][j],parameter['z'][i][j],parameter['r'][i][j]=cal_h(parameter,i,j)
    return parameter
def backword(m,n,parameter): 
    for i in range(m-1,-1,-1):
        for j in range(n-1,-1,-1):
            parameter['e'][i][j]=epsilon(parameter,i,j,m,n)

            q=parameter['q'][i][j]
            h_con=parameter['h_con'][i][j]
            r=parameter['r'][i][j]
            s=parameter['s'][i][j]
            #其他导数的存储
            parameter['delta_z'][i][j]=delta_z(parameter,i,j)
            
            parameter['delta_pie'][i][j]=delta_pie(parameter,i,j)
            parameter['delta_r'][i][j]=delta_r(parameter,i,j)
            

            #参数导数的叠加
            parameter['dw_r']+=parameter['delta_r'][i][j].dot(q.T)
            parameter['dw_z']+=parameter['delta_z'][i][j].dot(q.T)
            
            parameter['db_r']+=parameter['delta_r'][i][j]           
            parameter['db_z']+=parameter['delta_z'][i][j]

    ##        
            parameter['dU']+=parameter['delta_pie'][i][j].dot((r*h_con).T)  
            parameter['dw']+=parameter['delta_pie'][i][j].dot(s.T)+parameter['e'][i][j].dot(s.T)
            parameter['db']+=parameter['delta_pie'][i][j]

            parameter['dw_m']+=parameter['e'][i][j].dot(((parameter['z'][i][j]*h_con).T))
            parameter['dU_m']+=parameter['e'][i][j]*parameter['h_pie'][i][j].dot((1-parameter['z'][i][j]).T)

    parameter['dw_s']=parameter['h'][-1][-1].T
    return parameter
    
def result(h,w_s):
    return w_s.dot(h[-1][-1])
def calhmn(parameter,datasets,index):
    m=np.shape(datasets[index])[0]
    n=np.shape(datasets[index])[1]
    parameter['s']=copy.deepcopy(datasets[index])
    #reset forward para
    parameter=initiallize_bin(parameter,m,n,d_h,d_s)
    #forward compute
    parameter=forward(m,n,parameter,d_h)
    hval=copy.deepcopy(parameter['h'])
    return hval 
    
def gradcheckfornewdata(dpara,para,sminus,splus,parameter,index=0,d_h=5):   
    left=dpara[-1][-1]
    
    parameter[para][-1][-1]+=1e-6
    hplus=calhmn(parameter,splus,index)
    hminus=calhmn(parameter,sminus,index)
 
    Jplus=testoutfornewdata(hminus,hplus,parameter['w_s'])

    parameter[para][-1][-1]-=2e-6
    
    hplus=calhmn(parameter,splus,index)
    hminus=calhmn(parameter,sminus,index)
    
    Jminus=testoutfornewdata(hminus,hplus,parameter['w_s'])
    
 
    print('our calculation of the derivative of the function',left)
    print('The derivative of the function calculate by the defination',((Jplus-Jminus)/(2e-6))[-1][-1])
def minbatch(parameter,sminus,splus,d_h,d_s,batch,rho,maskval,maxiter):
    loop=0
    while 1:
        innertime1=clock()
        loop+=1
        print('Loop:'+str(loop) )
        if loop==maxiter:
            break
        counter=0
        parameter=initiallize_grad(parameter,d_h,d_s)
        #初始化，设置为0 
        dw_r=np.zeros_like(parameter['dw_r'])
        dw_z=np.zeros_like(parameter['dw_z'])
        db_r=np.zeros_like(parameter['db_r'])
        db_z=np.zeros_like(parameter['db_z'])

        dU=np.zeros_like(parameter['dU'])
        dw=np.zeros_like(parameter['dw'])
        db=np.zeros_like(parameter['db'])
        dw_m=np.zeros_like(parameter['dw_m'])
        dU_m=np.zeros_like(parameter['dU_m'])

        dw_s=np.zeros_like(parameter['dw_s'])  
        #初始化adagrad方法的分母
        ada_dw_r=np.zeros_like(parameter['dw_r'])
        ada_dw_z=np.zeros_like(parameter['dw_z'])
        ada_db_r=np.zeros_like(parameter['db_r'])
        ada_db_z=np.zeros_like(parameter['db_z'])

        ada_dU=np.zeros_like(parameter['dU'])
        ada_dw=np.zeros_like(parameter['dw'])
        ada_db=np.zeros_like(parameter['db'])
        ada_dw_m=np.zeros_like(parameter['dw_m'])
        ada_dU_m=np.zeros_like(parameter['dU_m'])

        ada_dw_s=np.zeros_like(parameter['dw_s'])  

        for index in range(len(sminus)):
            #计算M(s+)
            m=np.shape(splus[index])[0]
            n=np.shape(splus[index])[1]
            #对于每一条输入数据，都初始化和参数无关的变量，包括h，e，h‘
            parameter=initiallize_grad(parameter,d_h,d_s)
            parameter=initiallize_bin(parameter,m,n,d_h,d_s)
            #传入输入
            parameter['s']=copy.deepcopy(splus[index])
            #前向计算
            parameter=forward(m,n,parameter,d_h)  
            result_plus=result(parameter['h'],parameter['w_s'])
            #后向计算        
            parameter=backword(m,n,parameter)   
            
            #计算M(S+)各个导数，直至batch次
            dw_r_plus=copy.deepcopy(parameter['dw_r'])
            dw_z_plus=copy.deepcopy(parameter['dw_z'])
            db_r_plus=copy.deepcopy(parameter['db_r'])
            db_z_plus=copy.deepcopy(parameter['db_z'])

            dU_plus=copy.deepcopy(parameter['dU'])
            dw_plus=copy.deepcopy(parameter['dw'])
            db_plus=copy.deepcopy(parameter['db'])
            dw_m_plus=copy.deepcopy(parameter['dw_m'])
            dU_m_plus=copy.deepcopy(parameter['dU_m'])

            dw_s_plus=copy.deepcopy(parameter['dw_s'])
     
            #计算M(S-),结构和上面相同
            m=np.shape(sminus[index])[0]
            n=np.shape(sminus[index])[1]
                
            parameter=initiallize_grad(parameter,d_h,d_s)
            parameter=initiallize_bin(parameter,m,n,d_h,d_s)
    
            parameter['s']=copy.deepcopy(sminus[index])
    
            parameter=forward(m,n,parameter,d_h)    
            result_minus=result(parameter['h'],parameter['w_s'])
            
            parameter=backword(m,n,parameter)
    
            dw_r_minus=copy.deepcopy(parameter['dw_r'])
            dw_z_minus=copy.deepcopy(parameter['dw_z'])
            db_r_minus=copy.deepcopy(parameter['db_r'])
            db_z_minus=copy.deepcopy(parameter['db_z'])

            dU_minus=copy.deepcopy(parameter['dU'])
            dw_minus=copy.deepcopy(parameter['dw'])
            db_minus=copy.deepcopy(parameter['db'])
            dw_m_minus=copy.deepcopy(parameter['dw_m'])
            dU_m_minus=copy.deepcopy(parameter['dU_m'])

            dw_s_minus=copy.deepcopy(parameter['dw_s'])  
            #对max函数求导
            if result_plus-result_minus<-4:
                pass
            else:
                #累加计算loss函数的导数，直至batch次        
                dw_r+=dw_r_plus-dw_r_minus
                dw_z+=dw_z_plus-dw_z_minus
                db_r+=db_r_plus-db_r_minus  
                db_z+=db_z_plus-db_z_minus
                
                dU+=dU_plus-dU_minus
                dw+=dw_plus-dw_minus
                db+=db_plus-db_minus
                dw_m+=dw_m_plus-dw_m_minus
                dU_m+=dU_m_plus-dU_m_minus
    
                dw_s+=dw_s_plus-dw_s_minus
                #当叠加batch次后
            
            counter+=1
            if counter==batch:
                
                #重置计数器
                counter=0
                #计算导数的均值
                ave_dw_r=dw_r/batch     
                ave_dw_z=dw_z/batch
                ave_db_r=db_r/batch
                ave_db_z=db_z/batch
        
                ave_dU=dU/batch
                ave_dw=dw/batch
                ave_db=db/batch
                ave_dw_m=dw_m/batch
                ave_dU_m=dU_m/batch

                ave_dw_s=dw_s/batch

                #计算adagrad的分母
                ada_dw_r+=ave_dw_r*ave_dw_r
                ada_dw_z+=ave_dw_z*ave_dw_z
                ada_db_r+=ave_db_r*ave_db_r
                ada_db_z+=ave_db_z*ave_db_z
                
                ada_dU+=ave_dU*ave_dU
                ada_dw+=ave_dw*ave_dw
                ada_db+=ave_db*ave_db
                ada_dw_m+=ave_dw_m*ave_dw_m
                ada_dU_m+=ave_dU_m*ave_dU_m
                
                ada_dw_s+=ave_dw_s*ave_dw_s 

#                print ('lambda',(rho[0]/np.sqrt(ada_dw_r_l)))
#                print('grad',ave_dw_r_l)
                #更新参数
#                print(1)



                mask=dict()
               
                if maskval==1:


                    for i in range(2):
                        maskseed=np.random.binomial(1,0.5,np.shape(parameter['w_r'])[0])
                        mask[i]=np.zeros_like(parameter['w_r'])
                        for line in range(len(mask[i])):
                            for col in range(len(mask[i][0])):
                                if maskseed[line]==1:
                                    mask[i][line][col]=1
                    for i in range(2,4):
                        maskseed=np.random.binomial(1,0.5,np.shape(parameter['b_r'])[0])
                        mask[i]=np.zeros_like(parameter['b_r'])
                        for line in range(len(mask[i])):
                            for col in range(len(mask[i][0])):
                                if maskseed[line]==1:
                                    mask[i][line][col]=1

                    maskseed=np.random.binomial(1,0.5,np.shape(parameter['U'])[0])
                    mask[4]=np.zeros_like(parameter['U'])
                    for line in range(len(mask[4])):
                        for col in range(len(mask[4][0])):
                            if maskseed[line]==1:
                                mask[4][line][col]=1

                    maskseed=np.random.binomial(1,0.5,np.shape(parameter['w'])[0])
                    mask[5]=np.zeros_like(parameter['w'])
                    for line in range(len(mask[5])):
                        for col in range(len(mask[5][0])):
                            if maskseed[line]==1:
                                mask[5][line][col]=1

                    maskseed=np.random.binomial(1,0.5,np.shape(parameter['b'])[0])
                    mask[6]=np.zeros_like(parameter['b'])
                    for line in range(len(mask[6])):
                        for col in range(len(mask[6][0])):
                            if maskseed[line]==1:
                                mask[6][line][col]=1
                    maskseed=np.random.binomial(1,0.5,np.shape(parameter['w_m'])[0])
                    mask[7]=np.zeros_like(parameter['w_m'])
                    for line in range(len(mask[7])):
                        for col in range(len(mask[7][0])):
                            if maskseed[line]==1:
                                mask[7][line][col]=1
                    maskseed=np.random.binomial(1,0.5,np.shape(parameter['U_m'])[0])
                    mask[8]=np.zeros_like(parameter['U_m'])
                    for line in range(len(mask[8])):
                        for col in range(len(mask[8][0])):
                            if maskseed[line]==1:
                                mask[8][line][col]=1
                    maskseed=np.random.binomial(1,0.5,np.shape(parameter['w_s'])[0])
                    mask[9]=np.zeros_like(parameter['w_s'])
                    for line in range(len(mask[9])):
                        for col in range(len(mask[9][0])):
                            if maskseed[line]==1:
                                mask[9][line][col]=1


                elif maskval==0:
                    mask[0]=np.ones_like(parameter['w_r'])
                    mask[1]=np.ones_like(parameter['w_z'])
                    mask[2]=np.ones_like(parameter['b_r'])
                    mask[3]=np.ones_like(parameter['b_z'])

                    mask[4]=np.ones_like(parameter['U'])
                    mask[5]=np.ones_like(parameter['w'])
                    mask[6]=np.ones_like(parameter['b'])
                    mask[7]=np.ones_like(parameter['w_m'])
                    mask[8]=np.ones_like(parameter['U_m'])

                    mask[9]=np.ones_like(parameter['w_s'])
                
                
                #mask                    
                parameter['w_r']-=ave_dw_r*(rho[0]/np.sqrt(ada_dw_r))*mask[0]
                parameter['w_z']-=ave_dw_z*(rho[1]/np.sqrt(ada_dw_z))*mask[1]
                parameter['b_r']-=ave_db_r*(rho[2]/np.sqrt(ada_db_r))*mask[2]
                parameter['b_z']-=ave_db_z*(rho[3]/np.sqrt(ada_db_z))*mask[3]

                parameter['U']-=ave_dU*(rho[4]/np.sqrt(ada_dU))*mask[4]
                parameter['w']-=ave_dw*(rho[5]/np.sqrt(ada_dw))*mask[5]
                parameter['b']-=ave_db*(rho[6]/np.sqrt(ada_db))*mask[6]
                parameter['w_m']-=ave_dw_m*(rho[7]/np.sqrt(ada_dw_m))*mask[7]
                parameter['U_m']-=ave_dU_m*(rho[8]/np.sqrt(ada_dU_m))*mask[8]

                parameter['w_s']-=ave_dw_s*(rho[9]/np.sqrt(ada_dw_s))*mask[9]
                
                
                #导数初始化，设置为0 
                dw_r=np.zeros_like(parameter['dw_r'])
                dw_z=np.zeros_like(parameter['dw_z'])
                db_r=np.zeros_like(parameter['db_r'])
                db_z=np.zeros_like(parameter['db_z'])

                dU=np.zeros_like(parameter['dU'])
                dw=np.zeros_like(parameter['dw'])
                db=np.zeros_like(parameter['db'])
                dw_m=np.zeros_like(parameter['dw_m'])
                dU_m=np.zeros_like(parameter['dU_m'])

                dw_s=np.zeros_like(parameter['dw_s'])
        innertime2=clock()
        print('one batch cost: '+str(innertime2-innertime1)+' s')
        parameter['result'].append(4+result_plus-result_minus)
        print('Loss: '+str(4+result_plus-result_minus))
    return parameter

    
def initiallize_parameter(d_h,d_s,con=100):

    parameter=dict()
    parameter['w_r']=np.random.uniform(-np.sqrt(1./(d_s+6*d_h)),np.sqrt(1./(d_s+6*d_h)),(3*d_h,d_s+3*d_h))/con
    parameter['w_z']=np.random.uniform(-np.sqrt(1./(d_s+6*d_h)),np.sqrt(1./(d_s+6*d_h)),(3*d_h,d_s+3*d_h))/con
    parameter['b_r']=np.random.uniform(-np.sqrt(1./3*d_h), np.sqrt(1./3*d_h),(3*d_h,1))/con
    parameter['b_z']=np.random.uniform(-np.sqrt(1./3*d_h), np.sqrt(1./3*d_h),(3*d_h,1))/con

    
    parameter['w']=np.random.uniform(-np.sqrt(1./(d_s+d_h)), np.sqrt(1./(d_s+d_h)),(d_h,d_s))/con
    parameter['U']=np.random.uniform(-np.sqrt(1./(4*d_h)), np.sqrt(1./(4*d_h)),(d_h,3*d_h))/con
    parameter['b']=np.random.uniform(-np.sqrt(1./d_h), np.sqrt(1./d_h),(d_h,1))/con
    
    parameter['w_m']=np.random.uniform(-np.sqrt(1./4*d_h), np.sqrt(1./4*d_h),(d_h,3*d_h))/con
    parameter['U_m']=np.random.uniform(-np.sqrt(1./4*d_h), np.sqrt(1./4*d_h),(d_h,3*d_h))/con

    parameter['w_s']=np.random.uniform(-np.sqrt(1./d_h), np.sqrt(1./d_h),(1,d_h))/con
    parameter['b_s']=np.random.rand(1)/con
    parameter['result']=[]
    return parameter
    
def initiallize_grad(parameter,d_h,d_s,con=100):
    parameter['dw_r']=np.zeros((3*d_h,d_s+3*d_h))
    parameter['dw_z']=np.zeros((3*d_h,d_s+3*d_h))
    parameter['db_r']=np.zeros((3*d_h,1))
    parameter['db_z']=np.zeros((3*d_h,1))
    
    parameter['dw']=np.zeros((d_h,d_s))
    parameter['dU']=np.zeros((d_h,3*d_h))
    parameter['db']=np.zeros((d_h,1))

    parameter['dw_m']=np.zeros((d_h,3*d_h))
    parameter['dU_m']=np.zeros((d_h,3*d_h))

    parameter['dw_s']=np.zeros((1,d_h))
    parameter['db_s']=np.zeros((1)) 
    return parameter
    
def initiallize_bin(parameter,m,n,d_h,d_s,con=100):
    parameter['h']=np.zeros((m,n,d_h,1))
    parameter['e']=np.zeros((m,n,d_h,1))
    parameter['h_pie']=np.zeros((m,n,d_h,1))

    parameter['z']=np.zeros((m,n,3*d_h,1))
    parameter['r']=np.zeros((m,n,3*d_h,1))
    parameter['delta_r']=np.zeros((m,n,3*d_h,1))
    parameter['delta_z']=np.zeros((m,n,3*d_h,1))


    parameter['delta_pie']=np.zeros((m,n,d_h,1))

    parameter['q']=np.zeros((m,n,3*d_h+d_s,1))
    parameter['h_con']=np.zeros((m,n,3*d_h,1))
    return parameter
def testout(h,w_s,b_s):
    return w_s.dot(h[-1][-1])+b_s
def gradcheck(para,parameter):       

    parameter[para][-1][-1]+=1e-6
    hplus=calhmn(parameter,sminus,index)
    
    Jplus=testout(hplus,parameter['w_s'],parameter['b_s'])   
    parameter[para][-1][-1]-=2e-6
    
    hplus=calhmn(parameter,sminus,index)
    
    Jminus=testout(hplus,parameter['w_s'],parameter['b_s']) 
    print('The derivative of the function calculate by the defination',((Jplus-Jminus)/(2e-6))[0][0]) 
    
    
def make_rho():
    rho=np.zeros(18)
    rho[0]=1e-16
    rho[1]=1e-12
    rho[2]=1e-12
    rho[3]=1e-7
    rho[4]=1e-8
    rho[5]=1e-11
    rho[6]=1e-4
    rho[7]=1e-7
    rho[8]=1e-5
    rho[9]=1e-4
    return rho

import pickle
from time import clock

with open(u'C:\\Users\\Lab\\Desktop\\实验\欧氏距离归一化数据\\S_reduce.txt','rb') as f:   
    sminus=pickle.load(f)
with open(u'C:\\Users\\Lab\\Desktop\\实验\欧氏距离归一化数据\\S_plus.txt','rb') as f:   
    splus=pickle.load(f)


d_h=5;d_s=1
parameter=initiallize_parameter(d_h,d_s)
wrt=copy.deepcopy(parameter)
rho=make_rho()*10000

start=clock()
parameter=minbatch(parameter,sminus,splus,d_h,d_s,10,rho,1,150)
end=clock()
print('runtime:',end-start)

with open(u'result_5.7_rhomulti5000_dropout_lossplot_new_No3_10batch_150iter.txt','wb') as f:   
    pickle.dump(parameter,f)



