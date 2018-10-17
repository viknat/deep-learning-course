import torch, torchvision
import numpy as np
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import accuracy_score
import random


class AffineLayer:
    def __init__(self, in_dim, out_dim):
        xavier_std = 2 / in_dim
        self.weights = np.random.normal(scale=xavier_std, size=(out_dim, in_dim))
        self.bias_weights = np.array([0.01] * out_dim).reshape(out_dim, 1)

    def forward(self, inputs):
        self.inputs = inputs
        self.forward_product = np.dot(self.weights, inputs) + self.bias_weights
        return self.forward_product

    def backward(self, cache):
        average_inputs = self.inputs
        self.gradient = np.outer(cache, average_inputs)
        self.bias_weights = np.multiply(cache, self.bias_weights)
        self.new_cache = np.dot(self.weights.T, cache)
        return self.new_cache
  
    
class ReluLayer:
    def __init__(self, dim):
        self.dim = dim

    def forward(self, inputs):
        self.inputs = inputs
        relu = np.vectorize(lambda x: max(x, 0.0))
        self.forward_product = relu(inputs)
        return self.forward_product

    def backward(self, cache):
        self.gradient = np.where(self.forward_product == 0.0, 0.0, cache)
        return self.gradient

    
class SoftmaxLayer:
    def __init__(self, in_dim):
        self.in_dim = in_dim

    def forward(self, inputs):
        self.inputs = inputs
        e_x = np.exp(inputs - np.max(inputs))
        self.forward_product = e_x / e_x.sum(axis=0)
        return self.forward_product

    def backward(self, y_true):
        self.gradient = (self.forward_product - y_true)
        self.gradient = self.gradient.mean(axis=1)
        self.gradient = self.gradient.reshape(len(self.gradient), 1)
        return self.gradient

    
class NeuralNetwork:
    def __init__(self, layer_dimensions):
        self.layer_dimensions = layer_dimensions
        self.layers = []

        for in_dim, out_dim in zip(self.layer_dimensions[:-1], 
                                   self.layer_dimensions[1:]):
            affine_layer = AffineLayer(in_dim, out_dim)
            self.layers.append(affine_layer)
            relu_layer = ReluLayer(out_dim)
            self.layers.append(relu_layer)
        _ = self.layers.pop() # Remove last Relu layer
        softmax_layer = SoftmaxLayer(self.layer_dimensions[-1])
        self.layers.append(softmax_layer)

    def forward_pass(self, X):
        input_vector = X
        for layer in self.layers:
            output = layer.forward(input_vector)
            input_vector = output
        return output

    def cost_function(self, AL, y, epsilon=1e-12):
        AL = np.clip(AL.T, epsilon, 1. - epsilon)
        N = AL.shape[0]
        ce = -np.sum(np.multiply(y.T, np.log(AL+1e-9)))/N
        return ce

    def backward_pass(self, y_true):
        grad_so_far = y_true
        for i, layer in enumerate(reversed(self.layers)):
            grad = layer.backward(grad_so_far)
            grad_so_far = grad

    def update_parameters(self, alpha):
        for layer in self.layers:
            if isinstance(layer, AffineLayer):
                layer.weights = layer.weights - (alpha * layer.gradient)
                
    def get_accuracy_score(self, X, y):
        y_pred = self.predict(X.T)
        preds_vec = y_pred.argmax(axis=0)
        return accuracy_score(y.argmax(axis=1), preds_vec.T)

    def train(self, X_train, X_val, y_train, y_val, iters=2000, alpha=0.01,
    batch_size=100):

        random_indices = np.random.permutation(X_train.shape[0])
        losses = []
        for i in range(iters):
            sgd_index = random_indices[i % X_train.shape[0]]
            X_sample, y_sample = X_train[sgd_index].reshape(1,-1), y_train[sgd_index].reshape(1,-1)
            preds = self.forward_pass(X_sample.T)
            loss = self.cost_function(preds, y_sample.T)
            losses.append(loss)
            self.backward_pass(y_sample.T)
            if i % 1999 == 0:
                train_loss = np.mean(losses)
                train_accuracy = self.get_accuracy_score(X_train, y_train)
                val_preds = self.forward_pass(X_val.T)
                val_loss = self.cost_function(val_preds, y_val.T)
                val_accuracy = self.get_accuracy_score(X_val, y_val)
                print ("Iter %s: Training Loss %.3f, Training Accuracy %.3f Validation Loss %.3f Validation accuracy %.3f" % (
                    i, train_loss, train_accuracy, val_loss, val_accuracy))
            self.update_parameters(alpha)

    def predict(self, X_new):
        preds = self.forward_pass(X_new) 
        return preds

def get_data():
    transform = torchvision.transforms.Compose(
    [torchvision.transforms.ToTensor(),
    torchvision.transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])
    trainset = torchvision.datasets.CIFAR10(root='./data', train=True,
    download=True, transform=transform)
    testset = torchvision.datasets.CIFAR10(root='./data', train=False,
    download=True, transform=transform)

    X_train = trainset.train_data.reshape(50000, 3072)
    X_test = testset.test_data.reshape(10000, 3072)

    #One-hot encoding of labels
    y_train = np.array(trainset.train_labels)
    y_train = OneHotEncoder().fit_transform(y_train.reshape(-1, 1)).todense()
    y_test = np.array(testset.test_labels)
    y_test = OneHotEncoder().fit_transform(y_test.reshape(-1, 1)).todense()

    #Scale data
    scaler = StandardScaler()
    scaler.fit(X_train, y_train)
    X_train = scaler.transform(X_train)
    X_test = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test

def split_train_val_sets(X_train, y_train, val_pct=0.1):
    n_validation = int(val_pct * X_train.shape[0])
    indices = np.random.permutation(X_train.shape[0])
    val_idx, train_idx = indices[:n_validation], indices[n_validation:]
    X_val, y_val = X_train[val_idx], y_train[val_idx]
    X_train, y_train = X_train[train_idx], y_train[train_idx]
    return X_train, X_val, y_train, y_val

if __name__ == '__main__':
    X_train, X_test, y_train, y_test = get_data()
    X_train, X_val, y_train, y_val = split_train_val_sets(X_train, y_train)
    random.seed(43)

    nn = NeuralNetwork([3072, 1600, 10])
    nn.train(X_train, X_val, y_train, y_val, alpha=0.0007, iters=100000)

    X_train, X_val, y_train, y_val = split_train_val_sets(X_train, y_train)

    X_train.shape, X_val.shape, y_train.shape, y_val.shape

    import random
    random.seed(43)

    nn = NeuralNetwork([3072, 1600, 10])
    nn.train(X_train, X_val, y_train, y_val, alpha=0.0007, iters=100000)
