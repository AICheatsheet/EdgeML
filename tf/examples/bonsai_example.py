import preprocess
import tensorflow as tf
import numpy as np
import sys
sys.path.insert(0, '../')

from edgeml.trainer.bonsaiTrainer import BonsaiTrainer
from edgeml.graph.bonsai import Bonsai


def preProcessData(data_dir):
    '''
    Function to pre-process input data
    Expects a .npy file of form [lbl feats] for each datapoint
    Outputs a train and test set datapoints appended with 1 for Bias induction
    dataDimension, numClasses are inferred directly
    '''
    train = np.load(data_dir + '/train.npy')
    test = np.load(data_dir + '/test.npy')

    dataDimension = int(train.shape[1]) - 1

    Xtrain = train[:, 1:dataDimension + 1]
    Ytrain_ = train[:, 0]
    numClasses = max(Ytrain_) - min(Ytrain_) + 1

    Xtest = test[:, 1:dataDimension + 1]
    Ytest_ = test[:, 0]

    numClasses = int(max(numClasses, max(Ytest_) - min(Ytest_) + 1))

    # Mean Var Normalisation
    mean = np.mean(Xtrain, 0)
    std = np.std(Xtrain, 0)
    std[std[:] < 0.000001] = 1
    Xtrain = (Xtrain - mean) / std

    Xtest = (Xtest - mean) / std
    # End Mean Var normalisation

    lab = Ytrain_.astype('uint8')
    lab = np.array(lab) - min(lab)

    lab_ = np.zeros((Xtrain.shape[0], numClasses))
    lab_[np.arange(Xtrain.shape[0]), lab] = 1
    if (numClasses == 2):
        Ytrain = np.reshape(lab, [-1, 1])
    else:
        Ytrain = lab_

    lab = Ytest_.astype('uint8')
    lab = np.array(lab) - min(lab)

    lab_ = np.zeros((Xtest.shape[0], numClasses))
    lab_[np.arange(Xtest.shape[0]), lab] = 1
    if (numClasses == 2):
        Ytest = np.reshape(lab, [-1, 1])
    else:
        Ytest = lab_

    trainBias = np.ones([Xtrain.shape[0], 1])
    Xtrain = np.append(Xtrain, trainBias, axis=1)
    testBias = np.ones([Xtest.shape[0], 1])
    Xtest = np.append(Xtest, testBias, axis=1)

    return dataDimension + 1, numClasses, Xtrain, Ytrain, Xtest, Ytest


def dumpCommand(list, currDir):
    '''
    Dumps the current command to a file for further use
    '''
    commandFile = open(currDir + '/command.txt', 'w')
    command = "python"

    command = command + " " + ' '.join(list)
    commandFile.write(command)

    commandFile.flush()
    commandFile.close()


# Fixing seeds for reproducibility
tf.set_random_seed(42)
np.random.seed(42)

# Hyper Param pre-processing
args = preprocess.getBonsaiArgs()

sigma = args.sigma
depth = args.depth

projectionDimension = args.projDim
regZ = args.rZ
regT = args.rT
regW = args.rW
regV = args.rV

totalEpochs = args.epochs

learningRate = args.learningRate

data_dir = args.data_dir

outFile = args.output_file

(dataDimension, numClasses,
    Xtrain, Ytrain, Xtest, Ytest) = preProcessData(data_dir)

sparZ = args.sZ

if numClasses > 2:
    sparW = 0.2
    sparV = 0.2
    sparT = 0.2
else:
    sparW = 1
    sparV = 1
    sparT = 1

if args.sW is not None:
    sparW = args.sW
if args.sV is not None:
    sparV = args.sV
if args.sT is not None:
    sparT = args.sT

if args.batchSize is None:
    batchSize = np.maximum(100, int(np.ceil(np.sqrt(Ytrain.shape[0]))))
else:
    batchSize = args.batchSize

useMCHLoss = True

if numClasses == 2:
    numClasses = 1

X = tf.placeholder("float32", [None, dataDimension])
Y = tf.placeholder("float32", [None, numClasses])

currDir = preprocess.createTimeStampDir(data_dir)

dumpCommand(sys.argv, currDir)

# numClasses = 1 for binary case
bonsaiObj = Bonsai(numClasses, dataDimension,
                   projectionDimension, depth, sigma)

bonsaiTrainer = BonsaiTrainer(bonsaiObj,
                              regW, regT, regV, regZ,
                              sparW, sparT, sparV, sparZ,
                              learningRate, X, Y, useMCHLoss, outFile)

sess = tf.InteractiveSession()
sess.run(tf.group(tf.initialize_all_variables(),
                  tf.initialize_variables(tf.local_variables())))
saver = tf.train.Saver()

bonsaiTrainer.train(batchSize, totalEpochs, sess,
                    Xtrain, Xtest, Ytrain, Ytest, data_dir, currDir)

# For the following command:
# Data - Curet
# python2 bonsai_example.py -dir ./curet/ -d 2 -p 22 -rW 0.00001 -rZ 0.0000001 -rV 0.00001 -rT 0.000001 -sZ 0.4 -sW 0.5 -sV 0.5 -sT 1 -e 300 -s 0.1 -b 20
# Final Output - useMCHLoss = True
# Maximum Test accuracy at compressed model size(including early stopping): 0.940128 at Epoch: 278
# Final Test Accuracy: 0.926586

# Non-Zeros: 24231.0 Model Size: 115.65625 KB hasSparse: True

# Data - usps2
# python2 bonsai_example.py -dir usps2/ -d 2 -p 22 -rW 0.00001 -rZ 0.0000001 -rV 0.00001 -rT 0.000001 -sZ 0.4 -sW 0.5 -sV 0.5 -sT 1 -e 300 -s 0.1 -b 20
# Maximum Test accuracy at compressed model size(including early stopping): 0.95715 at Epoch: 299
# Final Test Accuracy: 0.952167

# Non-Zeros: 2636.0 Model Size: 19.1328125 KB hasSparse: True

# python3 bonsai_example.py -dir usps2/ -d 2 -p 22 -rW 0.00001 -rZ 0.0000001 -rV 0.00001 -rT 0.000001 -sZ 0.4 -sW 0.5 -sV 0.5 -sT 1 -e 300 -s 0.1 -b 20
# Maximum Test accuracy at compressed model size(including early stopping): 0.96113604 at Epoch: 163
# Final Test Accuracy: 0.94967616

# Non-Zeros: 2636.0 Model Size: 19.1328125 KB hasSparse: True