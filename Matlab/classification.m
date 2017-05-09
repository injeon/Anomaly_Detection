%% This function applies PCA in image classification

%% Initialization
% Define image dimensions (all the images have been resized to fit with
% this size
image_dims = [64 52];

% First read all the image names
input_dir = 'To_be_classified/';
filenames = dir(fullfile(input_dir, '*.jpg'));
num_images = numel(filenames);

% Initialize a list of images
images = zeros(prod(image_dims), num_images); 
for n = 1:num_images
    filename = fullfile(input_dir, filenames(n).name);
    img = imread(filename);
    img_resized = imresize(img,image_dims);
    images(:, n) = img_resized(1:end); % Add the image to the list; each column
    % represents an image and each row represents a component
    % Visualize imshow(reshape(images(:, 2),image_dims))
end

% Read labels
load('load_labels.mat');

%% Split the dataset into training set and testing set by 8:2 ratio
[train_index, test_index] = split(labels,0.8);
images_train = images(:,train_index);
images_test = images(:,test_index);
labels_train = labels(:,train_index);
labels_test = labels(:,test_index);

%% Use PCA to downsize the dimensions
% Preprocessing: mean-shifte the images
mean_face = mean(images, 2);
shifted_images = images - repmat(mean_face, 1, num_images);
 
% Calculate and ordere the eigenvectors and eigenvalues
% I used PCA instead of princomp() here because princomp will be abandoned
% by MATLAB
[evectors, score, evalues] = princomp(images');
% evectors: principal component coefficients/covariance matrix; 
% nxn matrix, where each column represents one principal components.
% score: the principal component scores; representation of X in the
% principal component space; row represents a sample and column represent a
% component
% latent: a vector containing the eigen values of the covariance matrix of
% x

% Only retain a certain number of top eigenvectors 
% Then we will have a n*p matrix, where each row represents a component in
% the original space, and each column represents a component in the new
% space
num_eigens = 20;
evectors = evectors(:,1:num_eigens); % n*p
 
% Project the images into the subspace to generate the feature vectors
% (n*p)' * (n*m) = p*m
features = evectors' * shifted_images;

% display the eigenvectors
figure;
for n = 1:num_eigens
    subplot(5, ceil(num_eigens/5), n);
    imshow(reshape(evectors(:,n),image_dims),[]);
end
saveas(gcf,'visual_evectors.png');
close

% display the eigenvalues
normalised_evalues = evalues / sum(evalues);
figure, plot(cumsum(normalised_evalues));
xlabel('No. of eigenvectors'), ylabel('Variance accounted for');
xlim([1 50]), ylim([0 1]), grid on;
saveas(gcf,'visual_variance.png');
close

%% Training
