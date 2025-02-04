#!/usr/bin/env python
# coding=utf-8
"""
   Alipay.com Inc.
   Copyright (c) 2004-2022 All Rights Reserved.
   ------------------------------------------------------
   File Name : lr_train_and_predict2_fast.py
   Author : qizhi.zqz
   Email: qizhi.zqz@alibaba-inc.com
   Create Time : 2022/9/2 上午10:07
   Description : description what the main function of this file
"""

from stensorflow.ml.nn.networks.DNN import DNN
import tensorflow as tf
from stensorflow.random.random import random_init
from stensorflow.basic.basic_class.private import PrivateTensor
from stensorflow.global_var import StfConfig
from stensorflow.engine.start_server import start_local_server, start_client
import time


start_local_server(config_file="../conf/config.json")
# start_client(config_file="../conf/config.json", job_name="workerR")


matchColNum = 1
featureNumL = 5
featureNumR = 5
record_num = 8429
epoch = 100   # 15
batch_size = 128

num_features = featureNumL + featureNumR
# dense_dims = [num_features, 7, 7, 1]       # the neural network structure is 32, 32, 1
dense_dims = [num_features, 1]
l2_regularization = 0.0
clip_value = 5.0

batch_num_per_epoch = record_num // batch_size
train_batch_num = epoch * batch_num_per_epoch + 1


learning_rate = 0.01

# -------------define a private tensor x_train of party L and a private tensor xyR_train on the party R

xL_train = PrivateTensor(owner='L')
xyR_train = PrivateTensor(owner='R')

format_x = [["a"]] * matchColNum + [[0.2]] * featureNumL
format_y = [["a"]] * matchColNum + [[0.3]] * featureNumR + [[1.0]]


# -----------------  load data from files -------------------

xL_train.load_from_file(path=StfConfig.train_file_onL,
                        record_defaults=format_x, batch_size=batch_size, repeat=epoch + 2, skip_col_num=matchColNum,
                        clip_value=clip_value)

xyR_train.load_from_file(path=StfConfig.train_file_onR,
                         record_defaults=format_y, batch_size=batch_size, repeat=epoch + 2, skip_col_num=matchColNum,
                         clip_value=clip_value)

# split xyR_train to features xR_train and label y_train
xR_train, y_train = xyR_train.split(size_splits=[featureNumR, 1], axis=1)

# ----------- build a DNN model (fully connected neural network)---------------

model = DNN(feature=xL_train, label=y_train, dense_dims=dense_dims, feature_another=xR_train)
model.compile()

# -------------start a tensorflow session, and initialize all variables -----------------
# sess = tf.compat.v1.Session(StfConfig.target, config=tf.compat.v1.ConfigProto(
#  device_count={"CPU":12},
#  inter_op_parallelism_threads=1,
#  intra_op_parallelism_threads=1
#  ))
sess = tf.compat.v1.Session(StfConfig.target)

init_op = tf.compat.v1.initialize_all_variables()
sess.run(init_op)


# -------------train the model ------------------------
start_time = time.time()

model.train_sgd(learning_rate=learning_rate, batch_num=train_batch_num, l2_regularization=l2_regularization, sess=sess)
# model.train_adam(sess=sess, batch_num=train_batch_num, learningRate=1E-3)
end_time = time.time()

print("train_time=", end_time-start_time)

# ------------define the private tensors for test dataset ----------------
pred_record_num = 12042*3//10
pred_batch_num = pred_record_num // batch_size

xL_test = PrivateTensor(owner='L')
xRy_test = PrivateTensor(owner='R')

xL_test.load_from_file(path=StfConfig.pred_file_onL,
                       record_defaults=format_x, batch_size=batch_size, repeat=2, skip_col_num=matchColNum,
                       clip_value=clip_value)

id = xRy_test.load_from_file_withid(path=StfConfig.pred_file_onR,
                                    record_defaults=format_y, batch_size=batch_size, repeat=2,
                                    id_col_num=matchColNum, clip_value=clip_value)

xR_test, y_test = xRy_test.split(size_splits=[-1, 1], axis=1)


# --------------predict --------------
model.predict_to_file(sess=sess, x=xL_test, x_another=xR_test,
                      predict_file_name=StfConfig.predict_to_file,
                      batch_num=pred_batch_num, idx=id)

sess.close()