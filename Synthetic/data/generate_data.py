import numpy as np
import random
import matplotlib.pyplot as plt

# Generate 100K numbers, each of which has 16 digits
# Anomaly: number of 1s is less than 4

# Set Parameteres
Anomaly_Threshold = 4 # Anomaly if total # 1s is less than the threshold

# Generate dataset
np.random.seed(9001)
n_dimensions = 16
n_samples = 10**5

mu = np.random.rand(n_dimensions) # Random vector for mean
cov = np.random.rand(n_dimensions,n_dimensions) # Random matrix for covaraince
data_mg = np.random.multivariate_normal(mu, cov, size=n_samples) # Generate a random matrix with multivariate normal distribution

data_bi = data_mg >= 0.5 # Convert to binary - True if the data is larger than 0.5; otherwise 0
data = data_bi*1 # Convert True/False to 1/0

# Label Anomaly if the number of 1s is less than the threshold
data_rowsum = np.sum(data,axis = 1)
labels = data_rowsum < Anomaly_Threshold # Anomaly if total # 1s is less than the threshold
labels = labels*1

print("Percentage of Anomaly in the dataset: " + str(np.sum(labels)/len(labels))) # Find percentage of anomaly in the dataset
print(data[labels == 1][:5]) # Print the first 5 rows of anomaly data as examples


if np.sum(labels)/len(labels) > 0.2:
    print("Too much anomaly: start cleaning!")
    labels_remove = (labels==1) & (np.random.rand(n_samples) <= 0.6) # Remove around 60% of anomalies
    print(str(sum(labels_remove)) +' Anomalies are going to be removed.')
    data = data[~labels_remove] # Remove the selected data
    labels = labels[~labels_remove] # Remove the corresponding labels
    print("Percentage of Anomaly in the dataset after cleaning: " + str(np.sum(labels)/len(labels))) # Find percentage of anomaly in the dataset

# Save the data and labels
np.save('data.npy',data)
np.save('labels.npy',labels)
print('Data and Labels have been saved!')