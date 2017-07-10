import numpy as np  
import pandas as pd  
import matplotlib.pyplot as plt  
from PIL import Image
from scipy.io import loadmat  
from scipy import stats  
from scipy.stats import multivariate_normal
import re
import glob
from operator import itemgetter 
import random
from random import shuffle
from keras.layers import Input, Dense
from keras.models import Model
from PCA_Functions import *
from sklearn.model_selection import KFold

def plot_images(imgs,labels):
    """
    To understand the data in image form: Plot 25 images selected randomly and add labels
    """
    ind = np.random.permutation(len(imgs))

    # Create figure with 5x5 sub-plots.
    fig, axes = plt.subplots(5, 5,figsize=(15,15))
    fig.subplots_adjust(hspace=0.1, wspace=0.01)

    for i, ax in enumerate(axes.flat): 
        ax.imshow(imgs[ind[i]], plt.cm.gray)
        if labels[ind[i]] == 1:
            xlabel = 'Anomaly'
        else:
            xlabel = 'Normal'
        # Show the classes as the label on the x-axis.
        ax.set_xlabel(xlabel)
        
        # Remove ticks from the plot.
        ax.set_xticks([])
        ax.set_yticks([])
    
    plt.show()

def show_anomaly_images(images,labels):
    """
    This function randomly show 9 images with label 1, which is anomaly
    """
    anomaly_label_index = np.asarray(np.where(labels)).reshape(-1) # Get the indice of anomaly
    anomaly_image = [images[i] for i in anomaly_label_index] # Extract the images labeled as anomaly
    anomaly_label = [labels[i] for i in anomaly_label_index] # Extract the images labeled as anomaly
    plot_images(anomaly_image,anomaly_label) # Show 9 images randomly

   
def plot_compare_after_reconst(img_matrix_reconst,imgs_matrix,height,width):
    """
    This function compares the images reconstructed after encoding & decoding with their original one.
    The shape of both image matrice in the input is m*n, where n is the number of components, 
    and m is the number of images.
    """
    # Permutate through the image index
    ind = np.random.permutation(imgs_matrix.shape[0])

    # Create figure with multiple sub-plots.
    fig, axes = plt.subplots(4, 4,figsize=(15,15))
    fig.subplots_adjust(hspace=0.1, wspace=0.01)

    # Initialize the counter of images
    image_count = 0 

    for i, ax in enumerate(axes.flat): 
        if i % 2 == 0:
            image_count += 1
            ax.imshow(imgs_matrix[ind[i],:].reshape(height,width), plt.cm.gray)
            xlabel = "Example {0}: Original Image".format(image_count)
        else:
            ax.imshow(img_matrix_reconst[ind[i-1],:].reshape(height,width), plt.cm.gray)
            xlabel = "Example {0}: Reconstructed Image".format(image_count)
        # Show the classes as the label on the x-axis.
        ax.set_xlabel(xlabel)

        # Remove ticks from the plot.
        ax.set_xticks([])
        ax.set_yticks([])

    plt.show()

def perm_and_split(m,ratio = 0.8):
    """
    This function generates random indices and split into two groups
    """
    ind = np.random.permutation(m) # Permutate to generate random indice within m
    size1 = int(m*ratio)
    group1 = ind[:size1-1]
    group2 = ind[size1:]
    return group1, group2

def split_training(labels,ratio = 0.8):
    """
    This function Split the Data into the Training and Validation Set. 
    Its output is the indice of images to be assigned to the Training/Validation Set. 
    The input "labels" is a hvector
    The ratio is a number between [0,1] that represents the percentage of images to be assigned to the training set
    """
    m = len(labels)
    training_size = int(m*ratio)
    while 1:
        ind = np.random.permutation(m) # Permutate to generate random indice within m
        train_ind = ind[:training_size-1]
        test_ind = ind[training_size:]
        # if (sum(itemgetter(*train_ind)(labels)) > 0 and sum(itemgetter(*test_ind)(labels)) > 0):
        if (sum(labels[train_ind]) > 0 and sum(labels[test_ind]) > 0):
            break
    return train_ind, test_ind

def split_data_labels_training_testing(data,labels,ratio_train = 0.8):
    """
    Function to split the data and labels into training and testing set
    """
    train_ind, test_ind = split_training(labels,ratio_train)

    data_train = data[train_ind]
    data_test = data[test_ind]

    labels_train = labels[train_ind]
    labels_test = labels[test_ind]

    return data_train,data_test,labels_train,labels_test

def split_train_eval_test(labels,ratio_train = 0.8, ratio_val = 0):
    """
    This function Split the Data into the Training, Evaluation, and Test Set,
    and there will be no anomalous sample in the training set.
    Its output is the indice of images to be assigned to the Training/Evaluation/Testing Set. 
    The input "labels" is a hvector
    The ratio is a number between [0,1] that represents the percentage of images to be assigned to the training/Evaluation set
    """
    m = len(labels) # Get the total number of labels
    ind = np.hstack(range(m)) # Generate an array of indices
    ind_anomal = ind[labels[:] == 1] # Get the indice of anomalous dataset
    ind_normal = ind[labels[:] == 0] # Get the indice of normal dataset

    shuffle(ind_normal) # Shuffle the Normal Dataset
    training_size = int(m*ratio_train) # Get the size of the training set
    val_size = int(m*ratio_val) # Get the size of the Validation Set
    train_ind = ind_normal[:training_size] # Split the Training Set; note: training set size can be 0
    nontraining_ind = np.concatenate((ind_normal[training_size:],ind_anomal),axis = 0) # Merge the remaining data
    shuffle(nontraining_ind) # Shuffle the indice of the nontraining set to mix the normal and anomalous dataset
    val_ind = nontraining_ind[:val_size] # Split the Evaluation Set
    test_ind = nontraining_ind[val_size:] # Split the Testing Set
    
    if ratio_val> 0:
        return train_ind, val_ind, test_ind
    else:
        return train_ind, test_ind # No validation set
        
def estimate_gaussian(X):
    """
    Compute the parameters of the Gaussian Distribution
    Note: X is given in the shape of m*k, where k is the number of (reduced) dimensions, and m is the number of images
    """
    mu = np.mean(X,axis=0)
    cov = np.cov(X,rowvar=0)

    return mu, cov

def fit_multivariate_gaussian(data,whitened = False, lam = 0, plot_comparison = False):
    """
    This function is used to compute the mu and cov based on the given data, and fit a multivariate gaussian dist
    This data is given as a m*k matrix, where m represents the number of samples, and k represents the number of dimensions
    """
    mu, cov = estimate_gaussian(data)
    if whitened:
        cov_dist = whitening_cov(cov, lam, plot_comparison)
    else:
        cov_dist = cov # No whitening
    dist = multivariate_normal(mean = mu, cov = cov_dist,allow_singular=False)
    return dist

def whitening_cov(cov,lam,plot_comparison = False):
    """
    This function whitenes the covariance matrix in order to make features less correlated with one another
    - cov: the original covariance of the original matrix
    - lam: the coefficient lambda for whitening the covariance
    - plot_comparison: trigger to plot the original covariance and whitened covariance for comparison
    """
    cov_whitened = lam*cov + (1-lam)*np.identity(cov.shape[0])
    if plot_comparison:
        compare_whiten_cov(cov,cov_whitened) # Plot for comparison
    return cov_whitened

def eval_prediction(pred,yval,k, rate = False):
    """
    Function to evaluate the correctness of the predictions with multiple metrics
    If rate = True, we will return all the metrics in rate (%) format (except f1)
    """
    true_positive = np.sum(np.logical_and(pred == 1, yval == 1)).astype(float) # True Positive
    true_negative = np.sum(np.logical_and(pred == 0, yval == 0)).astype(float) # True Negative
    false_positive = np.sum(np.logical_and(pred == 1, yval == 0)).astype(float) # False Positive
    false_negative = np.sum(np.logical_and(pred == 0, yval == 1)).astype(float) # False Negative

    precision = true_positive / max(1,true_positive + false_positive)
    recall = true_positive / max(1,true_positive + false_negative)
    f1 = (2 * precision * recall) / max(1,precision + recall)
    # Find the R-Precision
    RPrec,R = find_r_prec(pred, yval)
    # Find Precision k - if R < k, we will use R
    PrecK = find_prec_k(pred, yval,min(k,R))
    # A more direct version of f1 is f1 = 2*tp/(2*tp+fn+fp)
    
    if rate:
        n_p = sum(yval == 1)     # Number of Positive
        n_n = yval.shape[0] - n_p # Number of Negative
        tpr = true_positive/n_p
        tnr = true_negative/n_n
        fpr = false_positive/n_n
        fnr = false_negative/n_p
        return tpr,tnr,fpr,fnr,f1,RPrec,PrecK
    else:
        return true_positive,true_negative,false_positive,false_negative,f1,RPrec,PrecK

def find_euclidean_distance(matrix1,matrix2):
    """
    This function find the Euclidean Distance between two Matric
    The distance is between the same columns of two matric
    """
    dist = np.linalg.norm(matrix1 - matrix2,axis = 1) # By specifying axis = 0, we find the distance between columns
    return dist

def select_threshold_distance(edistance, yval,r, k=10, to_print = False):  
    """
    This function finds the best threshold value to detect the anomaly given the euclidean distance and True label Values
    edistance: euclidean distance 
    yval: True label value
    r: the number of relevant results for R-Precision test
    k: the k used to compute the precision at k in the testing set
    to_print: indicate if the result need to be printed
    """
    # Initialize the Metrics: only the selected will be used in optimization
    best_epsilon = 0
    best_f1 = 0

    # Sort the edistance and yval based on pval from high to low (in order to measure the Precision at K)
    rank = np.argsort(-edistance) # Sort from the Largest to the Smallest
    # If we want a rank from the smallest to the largest, we need to change the label here
    dist_ranked = edistance[rank] # Sort the edistance
    yval_ranked = yval[rank] # Sort the yval with the same order

    # Step Size
    step = (dist_ranked.max() - dist_ranked.min()) / 100

    for epsilon in np.arange(dist_ranked.min(), dist_ranked.max(), step):
        preds_ranked = dist_ranked > epsilon # If the distance is larger than the threshold, it will be identified as an anomaly

        tp,tn,fp,fn,f1,RPrec,precK = eval_prediction(preds_ranked,yval_ranked,k,rate = True)

        # Optimize to find the highest precision at k
        if f1 > best_f1:
            best_f1 = f1
            best_epsilon = epsilon

    # Get the best measurement with the best threshold
    if to_print: # Print out the result
        best_preds = dist_ranked > best_epsilon # If the pval is larger than the threshold, it will be identified as an anomaly
        eval_with_test(best_preds, yval_ranked, k) # Print out the result

    return best_epsilon

def select_threshold_probability(p, yval, k=10, to_print = False):  
    """
    This function finds the best threshold value to detect the anomaly given the PDF values and True label Values
    p: probability given by the Multivariate Gaussian Model
    yval: True label value
    k: the k used to compute the precision at k in the testing set
    to_print: indicate if the result need to be printed
    """
    # Initialize the Metrics: only the selected will be used in optimization
    best_epsilon = 0
    best_f1 = 0

    # Sort the edistance and yval based on pval from high to low (in order to measure the Precision at K)
    rank = np.argsort(p) # Sort from the smallest to the largest
    # If we want a rank from the smallest to the largest, we need to change the label here
    p_ranked = p[rank] # Sort the Probability
    yval_ranked = yval[rank] # Sort the yval with the same order

    # Step Size
    if p_ranked.max() == p_ranked.min(): # A horizontal line: No need to find epsilon
        best_epsilon = 0
        best_f1 = 0
    else:
        step = (p_ranked.max() - p_ranked.min()) / 100

        for epsilon in np.arange(p_ranked.min(), p_ranked.max(), step):
            preds_ranked = p_ranked < epsilon # If the probability is smaller than the threshold, it will be identified as an anomaly

            tp,tn,fp,fn,f1,RPrec,precK = eval_prediction(preds_ranked,yval_ranked,k,rate = True)

            # Optimize to find the highest precision at k
            if f1 > best_f1:
                best_f1 = f1
                best_epsilon = epsilon

    # Get the best measurement with the best threshold
    if to_print: # Print out the result
        best_preds = p_ranked < best_epsilon # If the pval is larger than the threshold, it will be identified as an anomaly
        eval_with_test(best_preds, yval_ranked, k) # Print out the result
        
    return best_epsilon

def convert_pred(pred,label_Anomaly,label_Normal):
    """
    This function converts the labels in pred into 0 and 1, where 0 indicates Normal, and 1 indicates Anomaly.
    Goal: Convert the data format before comparing to the Labels set for evaluation.
    label_Anomaly: the label used in the input pred set to indicate Anomaly
    label_Normal: the label used in the input pred set to indicate Normal
    """
    pred_output = pred # Copy the Dataset
    pred_output[pred == label_Normal] = 0  # Label the Normality with 0
    pred_output[pred == label_Anomaly] = 1 # Label the Anomalies as 1
    return pred_output


def evaluate_pred(Preds, Labels):
    """
    This function evaluate the Prediction with Labels. 
    Standard Format: Positive (Anomaly) is labeled with 1, and Negative (Normal) is labeled with 0
    """
    # Get the indices of the Positive and Negative Predictions
    ind_P = (Preds == 1)
    ind_N = (Preds == 0)
    # Evaluation
    TP = sum(((Preds[ind_P]) == 1) == ((Labels[ind_P]) == 1)) # True Positive
    TN = sum(((Preds[ind_N]) == 0) == ((Labels[ind_N]) == 0)) # True Negative
    FP = sum(((Preds[ind_P]) == 1) == ((Labels[ind_P]) == 0)) # False Positive
    FN = sum(((Preds[ind_N]) == 0) == ((Labels[ind_N]) == 1)) # False Negative
    TP, TN, FP, FN
    # Compute the Precision and Recall
    Recall = TP/max(1,TP+FN)
    Precision = TP/max(1,TP+FP)
    F = (2*Precision*Recall) / max(1,Precision+Recall)
    
    return Recall, Precision, F

def eval_with_test(Preds, Labels, k = 10,to_print = True):
    """
    Function to print out the metrices (for the evaluation on both the training and testing dataset)
    """
    # Find Recall, Precision, F score
    Recall, Precision, F = evaluate_pred(Preds, Labels)
    # Find the R-Precision
    RPrec,R = find_r_prec(Preds, Labels)
    # Find Precision k
    PrecK = find_prec_k(Preds, Labels,k)
    if to_print:
        print("Precision: {0:.1f}%".format(Precision * 100))
        print("Recall: {0:.1f}%".format(Recall * 100))
        print("F-score: {0:.1f}%".format(F * 100))
        print("R-Precision (# R = " + str(R) +  "): {0:.1f}%".format(RPrec * 100))
        print("Precision@" + str(k) +": {0:.1f}%".format(PrecK * 100))
        print()
    else:
        return Recall,Precision,F,RPrec,R,PrecK

def find_r_prec(Preds, Labels):
    """"
    Function to compute R-Precision: average precision for the first n results, where n = # relevant results (anomaly)
    """
    R = sum(Labels) # Total number of relevant data points (anomaly)
    RPrec = find_prec_k(Preds, Labels, R) # Use the find precision-k function to compute R-Precision
    return RPrec, R

def find_prec_k(Preds, Labels,k):
    """
    Compute the Precision at K
    """
    k = int(k) # ensure it is an integer
    PredsK = Preds[0:k] # Prediction at k
    LabelsK = Labels[0:k] # Labels at k
    ind_PK = (PredsK == 1) # Indices of Positive at K
    ind_NK = (PredsK == 0) # Indices of Negative at K
    TPK = np.sum((PredsK[ind_PK] == 1) == (LabelsK[ind_PK] == 1)) # True Positive at K
    FPK = np.sum((PredsK[ind_PK] == 1) == (LabelsK[ind_PK] == 0)) # False Positive at K
    PrecK = TPK/max(1,TPK + FPK) # Precision at K
    return PrecK


def plot_scatter_with_labels(dist,labels,plot_y_label):
    '''
    This function generates a scatter plot with labels to evaluate the detector
    '''
    # Sort the Images and Labels based on the Probability
    rank = np.argsort(-dist) # Sort from the Smallest to the Largest

    gaps_ranked = dist[rank]
    labels_ranked = labels[rank]


    length = labels_ranked.shape[0]
    counts = list(range(1,length+1))
    colors = labels_ranked == 0

    plt.figure(figsize=(15,8))
    plt.suptitle('Scatter Plot of the ' + plot_y_label,fontsize = 20)
    plt.xlabel('Ranking (ascending)',fontsize = 18)
    plt.ylabel(plot_y_label,fontsize = 18)
    plt.scatter(counts,gaps_ranked,c = colors,cmap=plt.cm.copper) 
    plt.ylim(min(gaps_ranked), max(gaps_ranked))
    plt.show()

def plot_matrix_data(matrix):
    """
    This function plots the distribution of data within a matrix for the purpose of observation
    """
    vector = matrix.flatten() # Convert to a Vector
    rank = np.argsort(vector) # Sort from the Smallest to the Largest
    vector_ranked = vector[rank]
    plt.figure(figsize=(15,8))
    plt.plot(vector_ranked)
    plt.title('The Distribution of Data within the Matrix',fontsize = 20)
    plt.xlabel('Ranking',fontsize = 18)
    plt.ylabel('Data Point Value',fontsize = 18)
    plt.show()

def label_anomaly(labels_input, anomaly_digit):
    """
    This function create a label vector to indicate anomaly. 
    input:
    - labels_input: the input labels vector that contains number 0-9 from MNIST
    - anomaly_digit: the target digit that we define as anomaly
    """
    labels_anomaly = np.zeros(labels_input.shape) # create a zero vector of the same length with the input label vector
    labels_anomaly[labels_input == anomaly_digit] = 1 # Mark the label of the anomaly digit as 1
    return labels_anomaly # return the newly created vector

def train_test_with_reconstruction_error(data_original_train, data_decoded_train, data_original_test, data_decoded_test, labels_train, labels_test,k,to_print = True):
    """
    Factorize the training and testing process of the Reconstruction Error-based method
    """
    ## Training
    # Find the euclidean distance between the original dataset and the decoded dataset
    dist_train = find_euclidean_distance(data_decoded_train,data_original_train)

    # Plot of the reconstruction error from high to low
    if to_print: 
        print("Below is a scatter plot that ranks the data points according to their Reconstruction Errors.")
        print("The higher the reconstruction error, the more likely the point will be detected as an anomaly")
        print("The Black Points are True Anomalies, while the others are True Normal points")
        plot_scatter_with_labels(dist_train,labels_train,"Reconstruction Error")
        print()

    # Get the number of actual anomaly for the R-precision
    r_train = sum(labels_train)
    # Train the Anomaly Detector
    if to_print:
        print("Training Results:")
        threshold_error = select_threshold_distance(dist_train, labels_train,r_train,k,to_print = to_print)
        print()
    else: # no print
        threshold_error = select_threshold_distance(dist_train, labels_train,r_train,k,to_print = to_print)

    ## Testing
    # Find the euclidean distance between the original dataset and the decoded dataset
    dist_test = find_euclidean_distance(data_decoded_test,data_original_test)

    # Sort the Images and Labels based on the Reconstruction Error
    rank_test = np.argsort(-dist_test) # Sort from the Largest to the Smallest
    dist_test_ranked = dist_test[rank_test] # Sort the Reconstruction Error
    # Rank Labels accoring to the same order
    labels_test_ranked = labels_test[rank_test]

    # Give Predictions
    preds = np.zeros(labels_test_ranked.shape) # Initialization
    preds[dist_test_ranked > threshold_error] = 1

    # Evaluate the Detector with Testing Data
    if to_print:# with print & no return
        print("Testing Results:")
        eval_with_test(preds, labels_test_ranked, k,to_print = to_print)
    else: # no print & with return
        Recall,Precision,F,RPrec,R,PrecK = eval_with_test(preds, labels_test_ranked, k,to_print = to_print)
        return Recall,Precision,F,RPrec,R,PrecK

def train_test_with_gaussian(data_train, data_test, labels_train, labels_test, k,whitened = False, lam = 0,folds = 2, plot_comparison = False,to_print = True):
    """
    Factorize the training and testing process of the Multivariate Gaussian-based method.
    Note:
    - whitened: a trigger to whitening the covariance
    - lam: the coefficient lambda for whitening the covariance
    - folds: number of folds used in k-fold cross validation
    - plot_comparison: trigger to plot the original covariance and whitened covariance for comparison
    """
    ## Training
    if whitened:
        # Apply Cross-Validation to find the best lambda
        dist = fit_gaussian_with_whiten_and_cv(data_train,labels_train,folds,k,plot_comparison=to_print)
    else:
        # Get Gaussian Distribution Model with the Training Data
        # Note: fit_multivariate_gaussian() is my own coded function
        dist = fit_multivariate_gaussian(data_train,whitened, plot_comparison,plot_comparison=to_print)

    # Get Probability of being Anomaly vs. being Normal
    p_train = dist.pdf(data_train)   # Probability of Being Normal

    ## Print training results
    # Plot the Probability with labels
    if to_print:
        plot_scatter_with_labels(p_train, labels_train,'Gaussian Probability')
        # Train the Anomaly Detector
        print("Training Results:")
    threshold_gaussian  = select_threshold_probability(p_train, labels_train, k, to_print = to_print)

    ## Testing
    # Find the euclidean distance between the reconstructed dataset and the original ()
    p_test = dist.pdf(data_test)   # Probability of Being Normal

    # Sort the Images and Labels based on the Probability
    rank_test = np.argsort(p_test) # Sort from the Smallest to the Largest
    p_test_ranked = p_test[rank_test] # Sort the distance
    labels_test_ranked = labels_test[rank_test] # Rank Labels

    # Give Predictions
    preds = np.zeros(labels_test_ranked.shape) # Initialization
    preds[p_test_ranked < threshold_gaussian] = 1 # If the probability is smaller than the threshold, marked as anomaly

    # Evaluate the Detector with Testing Data
    if to_print:# with print & no return
        print("Testing Results:")
        eval_with_test(preds, labels_test_ranked, k,to_print = to_print)
    else: # no print & with return
        Recall,Precision,F,RPrec,R,PrecK = eval_with_test(preds, labels_test_ranked, k,to_print = to_print)
        return Recall,Precision,F,RPrec,R,PrecK

def fit_gaussian_with_whiten_and_cv(data,labels,folds,k,to_print = True):
    """
    Here we fit a multivariate gaussian with whitening and cross validation
    """
    kf = KFold(n_splits = folds) # Create multiple folds for cross validation (cv)
    best_rprec_avg = 0 # Initialize the best average RPrec 
    best_f1_avg = -1 # Intialize a list to record the best lambda 
    lam_list = [] # list to record the lambda - for the plot
    f1_avg_list = []
    rprec_avg_list = [] # list to record the average RPrec corresponding to each lambda - used for the plot
    preck_avg_list = []
    
    for lam in frange(0,0.999,0.09): # Loop through each possible lambda (discretized)
        f1_list = []
        rprec_list = [] # Initialize a list to record the f1 score of each training & testing set combination
        preck_list = [] 
        for train_index, test_index in kf.split(data):
            
            # Training
            # training Use whitened covariance to fit a multivariate gaussian distribution
            data_train = data[train_index] # Get training set data
            labels_train = labels[train_index] # Get training set labels
            dist = fit_multivariate_gaussian(data_train,whitened=True,lam = lam) # Fit in a distribution 
            p_train = dist.pdf(data_train)   # Probability of Being Normal
            threshold_gaussian  = select_threshold_probability(p_train, labels_train, k, to_print = False) # Find the best threshold with the training set

            # Testing
            data_test = data[test_index] # Get the testing data
            labels_test = labels[test_index]
            p_test = dist.pdf(data_test)   # Probability of Being Normal

            # Sort the Images and Labels based on the Probability
            rank_test = np.argsort(p_test) # Sort from the Smallest to the Largest
            p_test_ranked = p_test[rank_test] # Sort the distance
            labels_test_ranked = labels_test[rank_test] # Rank Labels

            # Give Predictions
            preds = np.zeros(labels_test_ranked.shape) # Initialization
            preds[p_test_ranked < threshold_gaussian] = 1 # If the probability is smaller than the threshold, marked as anomaly

            tp,tn,fp,fn,f1,RPrec,precK = eval_prediction(preds,labels_test_ranked,k,rate = True)
            f1_list.append(f1) # Save the f1 score of the current training & testing combination
            preck_list.append(precK)
            rprec_list.append(RPrec)

        f1_avg = sum(f1_list)/len(f1_list) # The average f1 score for the current lambda
        rprec_avg = sum(rprec_list)/len(rprec_list)
        preck_avg = sum(preck_list)/len(preck_list)

        # Save the current lambda and rprec_avg
        lam_list.append(lam)
        f1_avg_list.append(f1_avg)
        rprec_avg_list.append(rprec_avg)
        preck_avg_list.append(preck_avg)

        # Optimize to find the highest f1
        if f1_avg > best_f1_avg:
            best_lam = lam # Record the current lambda
            best_f1_avg = f1_avg # Record the current target measurement
        if to_print:
            print('Finish evaluate Lambda: ' + str(lam))

    if to_print:
        plt.figure(figsize=(15,8))
        plt.subplot(1,2,1)
        plt.plot(lam_list, rprec_avg_list)
        plt.xlabel('Lambda')
        plt.ylabel('R-Precision')
        plt.title('R-Precision Achieved at Different Lambda')

        plt.subplot(1,2,2)
        plt.plot(lam_list, preck_avg_list)
        plt.xlabel('Lambda')
        plt.ylabel('Precision@'+str(k))
        plt.title('Precision@' +str(k)+' Achieved at Different Lambda')

        plt.show()

    # Print the best lambda
    if to_print:
        print('The best lambda selected from the cross validation is: ' + str(best_lam))

    # Use the optimal lambda and the entire data set to find the optimal dist
    dist = fit_multivariate_gaussian(data, whitened = True,lam = best_lam)
    return dist

def frange(start, stop, step):
    i = start
    while i < stop:
        yield i
        i += step

def scatter_plot_anomaly(data, labels,title = ''):
    """
    Creat a scatter plot of a 2D data contains anomaly
    """
    # print(int(labels[:20]))
    # plt.scatter(data[:,0],data[:,1])
    plt.scatter(data[:,0],data[:,1],c = labels)
    if len(title) > 0:
        plt.title(title)
    plt.show()

def plot_data_2d(data, labels):
    """
    This function creates a 2D Visualization of the input dataset and color with labels.
    Here I use PCA to downsize the multivariate input data into 2-Dimensions.
    Note: the input data has a shape of m*n, where m is the sample size and n is # of dimensions
    """
    n_components = 2
    # Compute PCA with training dataset
    data_encoded,n,m = pca_all_processes(data,labels,n_components,decode = False)
    
    # Print the % variance achieved with 2 PC
    compare_var(data,data_encoded, to_print = True)

    num_data = min(len(data),4000) # We plot in maximum 4000 points
    data_subset = data[:num_data]
    # Create a Scatterplot of the entire encoded data
    scatter_plot_anomaly(data_encoded, labels,'Scatterplot of the entire dataset')
    # Create multiple scatterplots of the subsets of the encoded data
    plot_data_subsets_2d(data_encoded,labels)
    
    
def plot_data_subsets_2d(data, labels):
    """
    This function takes a few subsets of data and creates scatterplots of each of them
    
    """
    # Shuffle the index
    ind = np.hstack(range(len(labels)))
    shuffle(ind)
    data_shuffled = data[ind]
    labels_shuffled = labels[ind]
    
    step_size = 500  # Number of points contained in each plot
    
    # Create figure with 5x5 sub-plots.
    fig, axes = plt.subplots(3, 3,figsize=(15,15))
    fig.subplots_adjust(hspace=0.1, wspace=0.01)

    for i, ax in enumerate(axes.flat): 
        start = i*step_size
        end = (i+1)*step_size
        data_subset = data_shuffled[start:end,:] # Get a subset of data with size 500 
        labels_subset = labels_shuffled[start:end] # Get the corresponding labels 
        ax.scatter(data_subset[:,0],data_subset[:,1],c = labels_subset)
        ax.set_title('Scatterplot of ' + str(step_size) + " sample points (No." + str(i+1)+")")
        # Remove ticks from the plot.
        ax.set_xticks([])
        ax.set_yticks([])
    
    plt.show()        

def plot_heatmap_of_cov(data):
    """
    This function plots a heatmap of the covariance matrix of the input data
    Note: the data is of the size m*n, where m is the sample size and n is the number of dimensions
    """
    print('Description of the data: ')
    print('# Data Points: ' + str(data.shape[0]))
    print('# Dimensions: ' + str(data.shape[1]))
    data_cov = np.cov(data,rowvar=0) # Compute the covariance of each dimensions across rows
    plot_heatmap(data_cov,'Heatmap of the covariance of the entire matrix')
    # plot_heatmap_of_cov_by_segments(data)
    

def plot_heatmap_of_cov_by_segments(data):
    """
    This function aims to plots multiple heatmaps of the covariance of the input data by segments.
    It selects a few columns each time, compute the covariance, and plot the heatmap.
    Note: the data is of the size m*n, where m is the sample size and n is the number of dimensions
    """
    n_dimensions = data.shape[1] # Number of dimensions = # columns
    for i in range(0, n_dimensions, 20):
        end = min(i+20,n_dimensions) # We cannot extract more dimensions than the total number
        data_cov_seg = np.cov(data[i:end,i:end],rowvar = 0)
        subtitle = 'Heatmap of covariance: Dimensions ' + str(i) + ' to '+ str(end)
        plot_heatmap(data_cov_seg,subtitle)
        
    
def plot_heatmap(data,title = ''):
    """
    This function plots a heatmap with the input data matrix 
    """
    plt.imshow(data, cmap='jet', interpolation='nearest') # Create a heatmap
    plt.colorbar() # Add a Color Bar by the side
    if len(title) > 0:
        plt.title(title)
    plt.show()

def plot_2datasets(data1,data2,title1 = '',title2 = ''):
    """
    This function plots the heatmaps of two input data matrix side by side 
    """
    plt.figure(figsize=(15,8))
    plt.subplot(1,2,1)
    plt.imshow(data1, cmap='jet', interpolation='nearest') # Create a heatmap
    if len(title1) > 0:
        plt.title(title1)
    plt.colorbar() # Add a Color Bar by the side

    plt.subplot(1,2,2)
    plt.imshow(data2, cmap='jet', interpolation='nearest') # Create a heatmap
    if len(title2) > 0:
        plt.title(title2)
    plt.colorbar() # Add a Color Bar by the side
    plt.show()
    
def compare_whiten_cov(cov,cov_whitened):
    """
    Plot the heatmatp of the covariance matrix vs. the whitened covariance side by side for comparison
    """
    plt.figure(figsize=(8,8))
    plt.subplot(1,2,1)
    plt.imshow(cov, cmap='jet', interpolation='nearest') # Create a heatmap
    plt.title('Plot of the original Covariance Matrix')
    plt.colorbar() # Add a Color Bar by the side

    plt.subplot(1,2,2)
    plt.imshow(cov_whitened, cmap='jet', interpolation='nearest') # Create a heatmap
    plt.title('Plot of the whitened Covariance Matrix')
    plt.colorbar() # Add a Color Bar by the side

    plt.show()


def compare_var(data, data_pca,pca_encoding_dimension,to_print = False):
    '''
    This function compare the % variance achieved with the PCA Encoding 
    '''
    var_retained = np.var(data_pca)/np.var(data)
    if to_print:
        dimension_origin = data.shape[1]
        print('Summary of PCA Encoding: ')
        print('Number of Dimension in the Original Dataset: ' + str(dimension_origin))
        print('Number of Dimension in the PCA-Encoded Dataset: '+ str(pca_encoding_dimension))
        print("{0:.1f}% variance is retained with the current PCA Reconstruction.".format(var_retained * 100))
        print()
    return var_retained

def evaludate_pc(data,labels):
    '''
    Evaluate the % variance retained with different number of pc
    '''
    var_retained_list = []
    n_components_list = []
    n_steps = 50 # To save the speed, in maximum we will evaluate 50 PC#s
    step_size = max(int(data.shape[1]/n_steps),1) 
    for n_components in range(0,data.shape[1]+1,step_size):
        data_pca,pca_matrix, component_mean = pca_all_processes(data,labels,n_components)
        var_retained = compare_var(data, data_pca,n_components)
        var_retained_list.append(var_retained)
        n_components_list.append(n_components)
    plt.plot(n_components_list,var_retained_list)
    plt.xlabel('# Components Retained after encoding')
    plt.ylabel('Varaince Retained with PCA Reconstruction')
    plt.title('Evaluation of the number of PC retained in PCA')
    plt.show()

def detection_with_pca_reconstruction_error(data_train, data_test,labels_train,labels_test,n_components,k,to_print = False,height=0,width=0):
    """
    Function to apply anomaly detection with PCA and Reconstruction Error
    """
    if to_print:
        evaludate_pc(data_train,labels_train) # Evaluate the % variance achieved at different #PC

    # Compute PCA with training dataset, and reconstruct the training dataset
    data_train_pca,pca_matrix,component_mean = pca_all_processes(data_train,labels_train,n_components,plot_eigenfaces_bool=to_print,plot_comparison_bool=to_print,height=height,width=width)
    # Reconstruct the test set
    data_test_pca = reconstruct_with_pca(data_test, component_mean,pca_matrix,n_components)

    if to_print: 
        compare_var(data_train, data_train_pca,n_components,to_print = to_print) # Find the % variance achieved at the current #PC

    # Anomaly Detection with Reconstruction Error
    if to_print: # Print result
        train_test_with_reconstruction_error(data_train, data_train_pca, data_test, data_test_pca, labels_train, labels_test,k,to_print = to_print)
    else:  # Return results in numeric values
        Recall,Precision,F,RPrec,R,PrecK = train_test_with_reconstruction_error(data_train, data_train_pca, data_test, data_test_pca, labels_train, labels_test,k,to_print = to_print)
        return Recall,Precision,F,RPrec,R,PrecK

def detection_with_pca_gaussian(data_train, data_test,labels_train,labels_test,n_components,k,to_print = False,height=0,width=0):
    """
    Function to apply anomaly detection with PCA and Gaussian
    """
    if to_print:
        evaludate_pc(data_train,labels_train) # Evaluate the % variance achieved at different #PC
    # Compute PCA with training dataset and encode the training dataset
    data_train_encoded,pca_matrix, component_mean = pca_all_processes(data_train,labels_train,n_components,plot_eigenfaces_bool = to_print,decode = False,height=height,width=width)
    # Encode the test set
    data_test_encoded = encode_pca(data_test, component_mean,pca_matrix,n_components)

    if to_print: 
        data_train_pca = reconstruct_with_pca(data_train, component_mean, pca_matrix, n_components) # Reconstruct with PCA
        compare_var(data_train, data_train_pca,n_components,to_print = to_print) # FInd the % variance achieved at the current #PC

    # Anomaly Detection with Reconstruction Error
    if to_print: # Print result
        train_test_with_gaussian(data_train_encoded, data_test_encoded, labels_train, labels_test,k,to_print=to_print)
    else:  # Return results in numeric values
        Recall,Precision,F,RPrec,R,PrecK = train_test_with_gaussian(data_train_encoded, data_test_encoded, labels_train, labels_test,k,to_print=to_print)
        return Recall,Precision,F,RPrec,R,PrecK
