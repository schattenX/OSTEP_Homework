# coding=utf-8
# python 3.8
from __future__ import print_function
import random
from optparse import OptionParser
import time
import matplotlib.pyplot as plt
import numpy as np


class malloc:
    def __init__(self, size, start, headerSize, policy, order, coalesce, align):
        # size of space
        self.size = size

        # info about pretend headers
        self.headerSize = headerSize

        # init free list
        self.freelist = []
        self.freelist.append((start, size))

        # keep track of ptr to size mappings
        # sizemap记录已经分配出去的内存空间
        self.sizemap = {}

        # policy
        self.policy = policy
        assert (self.policy in ['FIRST', 'BEST', 'WORST'])

        # list ordering
        self.returnPolicy = order
        assert (self.returnPolicy in ['ADDRSORT', 'SIZESORT+', 'SIZESORT-', 'INSERT-FRONT', 'INSERT-BACK'])

        # this does a ridiculous full-list coalesce, but that is ok
        self.coalesce = coalesce

        # alignment (-1 if no alignment)
        self.align = align
        assert (self.align == -1 or self.align > 0)

    def addToMap(self, addr, size):
        assert (addr not in self.sizemap)
        self.sizemap[addr] = size
        # print('adding', addr, 'to map of size', size)

    def malloc(self, size, alloc_policy):
        # 使地址为4的倍数
        if self.align != -1:
            left = size % self.align
            if left != 0:
                diff = self.align - left
            else:
                diff = 0
            # print('aligning: adding %d to %d' % (diff, size))
            size += diff

        size += self.headerSize

        self.policy = alloc_policy
        bestIdx = -1
        if self.policy == 'BEST':
            # Do not mix self.size with size
            bestSize = self.size + 1
        elif self.policy == 'WORST' or self.policy == 'FIRST':
            bestSize = -1

        count = 0
        # total_t1 = time.perf_counter()
        for i in range(len(self.freelist)):
            eaddr, esize = self.freelist[i][0], self.freelist[i][1]
            count += 1
            # 从freelist表中选择最靠近size的: 通过反复迭代，使得esize不断缩小，但必须要比size大
            if esize >= size and ((self.policy == 'BEST' and esize < bestSize) or
                                  (self.policy == 'WORST' and esize > bestSize) or
                                  (self.policy == 'FIRST')):
                bestAddr = eaddr
                bestSize = esize
                bestIdx = i
                if self.policy == 'FIRST':
                    break
        # total_t2 = time.perf_counter()
        # tot_cost = (total_t2 - total_t1) * 1000
        if bestIdx != -1:
            if bestSize > size:
                # print('SPLIT', bestAddr, size)
                self.freelist[bestIdx] = (bestAddr + size, bestSize - size)
                self.addToMap(bestAddr, size)
            elif bestSize == size:
                # print('PERFECT MATCH (no split)', bestAddr, size)
                self.freelist.pop(bestIdx)
                self.addToMap(bestAddr, size)
            else:
                print("should never get here")
                exit(1)
                # abort('should never get here')
            return (bestAddr, count)

        # print('*** FAILED TO FIND A SPOT', size)
        return (-1, count)

    def free(self, addr, sort_policy):
        # simple back on end of list, no coalesce
        if addr not in self.sizemap:
            return -1

        size = self.sizemap[addr]
        self.returnPolicy = sort_policy
        if self.returnPolicy == 'INSERT-BACK':
            self.freelist.append((addr, size))
        elif self.returnPolicy == 'INSERT-FRONT':
            self.freelist.insert(0, (addr, size))
        elif self.returnPolicy == 'ADDRSORT':
            self.freelist.append((addr, size))
            self.freelist = sorted(self.freelist, key=lambda e: e[0])
        elif self.returnPolicy == 'SIZESORT+':
            self.freelist.append((addr, size))
            self.freelist = sorted(self.freelist, key=lambda e: e[1], reverse=False)
        elif self.returnPolicy == 'SIZESORT-':
            self.freelist.append((addr, size))
            self.freelist = sorted(self.freelist, key=lambda e: e[1], reverse=True)

        # not meant to be an efficient or realistic coalescing...
        if self.coalesce == True:
            self.newlist = []
            self.curr = self.freelist[0]
            for i in range(1, len(self.freelist)):
                eaddr, esize = self.freelist[i]
                if eaddr == (self.curr[0] + self.curr[1]):
                    self.curr = (self.curr[0], self.curr[1] + esize)
                else:
                    self.newlist.append(self.curr)
                    self.curr = eaddr, esize
            self.newlist.append(self.curr)
            self.freelist = self.newlist

        del self.sizemap[addr]
        return 0

    def dump(self):
        print('Free List [ Size %d ]: ' % len(self.freelist), end='')
        for e in self.freelist:
            print('[ addr:%d sz:%d ]' % (e[0], e[1]), end='')
        print('')

    def reset(self, size, start):
        # size of space
        self.size = size
        # 初始化空闲列表
        self.freelist = []
        self.freelist.append((start, size))
        # keep track of ptr to size mappings
        # sizemap记录已经分配出去的内存空间
        self.sizemap = {}


#
# main program
#
parser = OptionParser()

parser.add_option('-s', '--seed', default=0, help='the random seed', action='store', type='int', dest='seed')
parser.add_option('-S', '--size', default=1024 * 10, help='size of the heap', action='store', type='int',
                  dest='heapSize')
parser.add_option('-b', '--baseAddr', default=1000, help='base address of heap', action='store', type='int',
                  dest='baseAddr')
parser.add_option('-H', '--headerSize', default=0, help='size of the header', action='store', type='int',
                  dest='headerSize')
parser.add_option('-a', '--alignment', default=-1, help='align allocated units to size; -1->no align', action='store',
                  type='int', dest='alignment')
parser.add_option('-p', '--policy', default='BEST', help='list search (BEST, WORST, FIRST)', action='store',
                  type='string', dest='policy')
parser.add_option('-l', '--listOrder', default='ADDRSORT',
                  help='list order (ADDRSORT, SIZESORT+, SIZESORT-, INSERT-FRONT, INSERT-BACK)', action='store',
                  type='string', dest='order')
parser.add_option('-C', '--coalesce', default=False, help='coalesce the free list?', action='store_true',
                  dest='coalesce')
parser.add_option('-n', '--numOps', default=1000, help='number of random ops to generate', action='store', type='int',
                  dest='opsNum')
parser.add_option('-r', '--range', default=10, help='max alloc size', action='store', type='int', dest='opsRange')
parser.add_option('-P', '--percentAlloc', default=50, help='percent of ops that are allocs', action='store', type='int',
                  dest='opsPAlloc')
parser.add_option('-A', '--allocList', default='', help='instead of random, list of ops (+10,-0,etc)', action='store',
                  type='string', dest='opsList')
parser.add_option('-c', '--compute', default=False, help='compute answers for me', action='store_true', dest='solve')

(options, args) = parser.parse_args()

m = malloc(int(options.heapSize), int(options.baseAddr), int(options.headerSize),
           options.policy, options.order, options.coalesce, options.alignment)

print('seed', options.seed)
print('size', options.heapSize)
print('baseAddr', options.baseAddr)
print('headerSize', options.headerSize)
print('alignment', options.alignment)
print('policy', options.policy)
print('listOrder', options.order)
print('coalesce', options.coalesce)
print('numOps', options.opsNum)
print('range', options.opsRange)
print('percentAlloc', options.opsPAlloc)
print('allocList', options.opsList)
print('compute', options.solve)
print('')

random.seed(options.seed)

percent = int(options.opsPAlloc) / 100.0
alloc_policies = ['FIRST', 'BEST', 'WORST']
sort_policies = ['ADDRSORT', 'SIZESORT+', 'SIZESORT-', 'INSERT-FRONT', 'INSERT-BACK']
color_lst = ['red', 'green', 'blue', 'orange', 'purple']
# 对于每一个分配策略算法，都要测试不同的释放策略对其性能的影响
for i in range(len(alloc_policies)):
    fig, ax = plt.subplots(2, 3)
    # ax.set_title("Influence of different sort policies to allocation policy: " + alloc_policies[i])
    for k in range(len(sort_policies)):
        # 重置Malloc类里面的空闲列表(freelist)，sizemap(分配的空间)，堆大小(heapsize)等参数
        # 由于只生成了一个Malloc实例，这个实例为所有排序策略和分配策略共有，若要防止——当前内存分配策略
        # 用完了堆空间，或者将堆空间切成许多外部碎片以至于干扰下一个内存分配策略的实验——这一情况，则必须
        # 重置Malloc实例的内部参数
        m.reset(options.heapSize, options.baseAddr)
        # 存储在一整个内存分配程序存在周期内(opsNum)的“内存分配”的消耗时间
        # 因为内存分配操作在时间上几乎是连续的，因此最后的图的趋势是连续的，
        # 是可以作为内存分配策略的性能反映的
        data_sets = []

        p = {}
        L = []
        assert (percent > 0)

        # 不带-A参数
        if options.opsList == '':
            c = 0  # 计数: 用于表示第几个分配的内存
            j = 0
            while j < int(options.opsNum):
                pr = False
                # 概率小于percent，则实现“分配内存”操作
                if random.random() < percent:
                    size = int(random.random() * int(options.opsRange)) + 1  # [1,Range]
                    # 计时1
                    total_t1 = time.perf_counter()
                    # old_time = datetime.datetime.now()
                    ptr, cnt = m.malloc(size, alloc_policies[i])
                    # new_time = datetime.datetime.now()
                    # 计时2
                    total_t2 = time.perf_counter()
                    # milliseconds
                    data_sets.append(((total_t2 - total_t1) * 1000))

                    if ptr != -1:
                        p[c] = ptr
                        L.append(c)
                    # print('ptr[%d] = Alloc(%d)' % (c, size), end='')
                    # if options.solve == True:
                    #     print(' returned %d (searched %d elements)' % (ptr + options.headerSize, cnt))
                    #     # print(' Cost time of malloc is %.5f ms' % ((T2 - T1) * 1000))
                    # else:
                    #     print(' returned ?')
                    c += 1
                    j += 1
                    pr = True
                # 概率大于等于percent，则实现“释放内存”操作
                else:
                    if len(p) > 0:
                        # pick random one to delete
                        d = int(random.random() * len(L))
                        rc = m.free(p[L[d]], sort_policies[k])
                        # print('Free(ptr[%d])' % L[d], )
                        # if options.solve == True:
                        #     print('returned %d' % rc)
                        # else:
                        #     print('returned ?')
                        del p[L[d]]
                        del L[d]
                        # print('DEBUG p', p)
                        # print('DEBUG L', L)
                        pr = True
                        j += 1
        # 转换成数组
        cost_arr = np.array(data_sets)
        # 绘图
        # 3 => ncol of subplots(nrow, ncol)
        row = int(k / 3)
        col = int(k % 3)
        ax[row, col].set_title(sort_policies[k])
        ax[row, col].set_ylim(0, 0.1)
        # ax[row, col].set_xlim(0, 5000)
        ax[row, col].grid(True)
        ax[row, col].margins(0)
        ax[row, col].set_xlabel("Times of Allocation")
        ax[row, col].set_ylabel("Cost of time(ms)")
        # x = np.array([s for s in range(seed_nums)])
        # print(len(x))
        ax[row, col].plot(cost_arr, color=color_lst[k])
        # ax[row, col].hlines(cost_mean, 0, 600, linestyles='dashed', label='mean value')
    # 防止子图的标题与其他图重叠
    plt.tight_layout()
    plt.savefig(alloc_policies[i] + ".png", dpi=227)
