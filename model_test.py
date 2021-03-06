
import env2048
import numpy as np
import tensorflow as tf

from collections import deque
import time

np.random.seed(2)
tf.set_random_seed(2)


OUTPUT_GRAPH = False
MAX_EPISODE = 3
DISPLAY_REWARD_THRESHOLD = 200
MAX_EP_STEPS = 1000
RENDER = False
GAMMA = 0.9
LR_A = 0.001
LR_C = 0.01

env = env2048.env2048(4,4)

N_F = env.observation_space
N_A = env.action_space


def deque_reduce_mean(deque) :
    maxlen = deque.maxlen - 1
    sum = 0
    for i in range(maxlen) :
        sum = sum + deque[i]
    mean = int(sum/deque.maxlen)
    #print('mean is ', mean)
    return mean

class Actor(object):
    def __init__(self, sess, n_features, n_actions, lr=0.001):
        self.sess = sess

        self.s = tf.placeholder(tf.float32, [1, n_features], "state")
        self.a = tf.placeholder(tf.int32, None, "act")
        self.td_error = tf.placeholder(tf.float32, None, "td_error")  # TD_error

        with tf.variable_scope('Actor'):
            w1 = tf.Variable(tf.random_normal(shape=[N_F, 10], mean=0., stddev=0.1), name='w1')
            l1 = tf.matmul(self.s, w1)
            l1 = tf.nn.relu(l1)

            w2 = tf.Variable(tf.random_normal(shape=[10, 10], mean=0., stddev=0.1), name='w2')
            l2 = tf.matmul(l1, w2)
            l2 = tf.nn.relu(l2)

            w3 = tf.Variable(tf.random_normal(shape=[10, 6], mean=0., stddev=0.1), name='w3')
            l3 = tf.matmul(l2, w3)
            l3 = tf.nn.relu(l3)

            w4 = tf.Variable(tf.random_normal(shape=[6, N_A], mean=0., stddev=0.1), name='w4')
            self.l4 = tf.matmul(l3, w4)
            self.hypo = tf.nn.softmax(self.l4)

        with tf.variable_scope('exp_v'):
            log_prob = tf.log(self.hypo[0, self.a])
            self.exp_v = tf.reduce_mean(log_prob * self.td_error)

        with tf.variable_scope('train'):
            self.train_op = tf.train.AdamOptimizer(lr).minimize(-self.exp_v)

    def learn(self, s, a, td):
        s = s[np.newaxis, :]
        feed_dict = {self.s: s, self.a: a, self.td_error: td}
        _, exp_v = self.sess.run([self.train_op, self.exp_v], feed_dict)
        return exp_v

    def choose_action(self, s):
        s = s[np.newaxis, :]
        probs = self.sess.run(self.hypo, {self.s: s})
        return np.random.choice(np.arange(probs.shape[1]), p=probs.ravel())

class Critic(object):
    def __init__(self, sess, n_features, lr=0.01):
        self.sess = sess

        self.s = tf.placeholder(tf.float32, [1, n_features], "state")
        self.v_ = tf.placeholder(tf.float32, [1, 1], "v_next")
        self.r = tf.placeholder(tf.float32, None, 'r')

        with tf.variable_scope('Critic'):
            w1 = tf.Variable(tf.random_normal(shape=[N_F, 10], mean=0., stddev=0.1), name='w1')
            l1 = tf.matmul(self.s, w1)
            l1 = tf.nn.relu(l1)

            w2 = tf.Variable(tf.random_normal(shape=[10, 6], mean=0., stddev=0.1), name='w2')
            l2 = tf.matmul(l1, w2)
            l2 = tf.nn.relu(l2)

            w3 = tf.Variable(tf.random_normal(shape=[6, 3], mean=0., stddev=0.1), name='w3')
            l3 = tf.matmul(l2, w3)
            l3 = tf.nn.relu(l3)

            w4 = tf.Variable(tf.random_normal(shape=[3, 1], mean=0., stddev=0.1), name='w4')
            self.l4 = tf.matmul(l3, w4)
            self.v = self.l4


        with tf.variable_scope('squared_TD_error'):
            self.td_error = self.r + GAMMA * self.v_ - self.v
            self.loss = tf.square(self.td_error)
        with tf.variable_scope('train'):
            self.train_op = tf.train.AdamOptimizer(lr).minimize(self.loss)

    def learn(self, s, r, s_):
        s, s_ = s[np.newaxis, :], s_[np.newaxis, :]

        v_ = self.sess.run(self.v, {self.s: s_})
        td_error, _ = self.sess.run([self.td_error, self.train_op],
                                          {self.s: s, self.v_: v_, self.r: r})
        return td_error

with tf.Session() as sess :

    actor = Actor(sess, n_features=N_F, n_actions=N_A, lr=LR_A)
    critic = Critic(sess, n_features=N_F, lr=LR_C)
    #saver = tf.train.import_meta_graph("./save_model/a2c/2048_a2c-final.ckpt.meta")
    saver = tf.train.Saver()
    saver.restore(sess, './save_model/a2c/75000/2048_a2c.ckpt')

    if OUTPUT_GRAPH:
        tf.summary.FileWriter("logs/", sess.graph)

    reward_sum = deque(maxlen=10)

    for i_episode in range(MAX_EPISODE):
        s = env.reset()
        t = 0
        track_r = []

        while True:
            a = actor.choose_action(s)

            s_, r, done = env.step(a)
            print('action : ', a)
            env.render()
            input()
            s = s_
            t += 1

            if done or t >= MAX_EP_STEPS:
                print('end')
                input()
                break
