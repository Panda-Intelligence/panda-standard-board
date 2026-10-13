"""Topology regressions; synthetic graphs are not native PCB acceptance."""
import copy
import random
import unittest
from pico47_branch_pruning import dangling_branch_ids as peel


def connected(edges, start, end):
    seen={start}; todo=[start]
    while todo:
        node=todo.pop()
        for a,b in edges.values():
            other=b if a==node else a if b==node else None
            if other is not None and other not in seen:
                seen.add(other);todo.append(other)
    return end in seen


class CopperBranches(unittest.TestCase):
    def test_whole_long_dead_tail(self):
        edges={f'e{i}':(str(i),str(i+1)) for i in range(120)}
        self.assertEqual(len(peel(edges,{'120'},{'e0'})),120)
    def test_stop_at_ground_via(self):
        self.assertEqual(peel({'a':('0','1'),'b':('1','2')},{'1'},{'a'}),['a'])
    def test_live_pad_to_pad_path_untouched(self):
        self.assertEqual(peel({'a':('0','1'),'b':('1','2')},{'0','2'},{'a'}),[])
    def test_stop_at_live_t_junction(self):
        edges={'tail':('x','t'),'left':('t','a'),'right':('t','b')}
        self.assertEqual(peel(edges,{'a','b'},{'tail'}),['tail'])
    def test_unseeded_branch_not_removed(self):
        edges={'a':('0','1'),'b':('2','3')}
        self.assertEqual(peel(edges,{'1','3'},{'a'}),['a'])
    def test_cycle_not_a_dead_tail(self):
        edges={'a':('0','1'),'b':('1','2'),'c':('2','0')}
        self.assertEqual(peel(edges,set(),{'a'}),[])
    def test_parallel_copper_is_not_degree_one(self):
        self.assertEqual(peel({'a':('0','1'),'b':('0','1')},set(),{'a'}),[])
    def test_self_loop_retained(self):
        self.assertEqual(peel({'a':('0','0')},set(),{'a'}),[])
    def test_no_seed_no_deletion(self):
        self.assertEqual(peel({'a':('0','1')},set(),set()),[])
    def test_no_input_mutation(self):
        edges={'a':('0','1'),'b':('1','2')};old=copy.deepcopy(edges)
        peel(edges,{'2'},{'a'});self.assertEqual(edges,old)
    def test_missing_seed_rejected(self):
        with self.assertRaises(ValueError):peel({'a':('0','1')},set(),{'missing'})
    def test_missing_anchor_rejected(self):
        with self.assertRaises(ValueError):peel({'a':('0','1')},{'missing'},{'a'})
    def test_malformed_edge_rejected(self):
        with self.assertRaises(ValueError):peel({'a':['0','1']},set(),{'a'})
    def test_empty_identity_rejected(self):
        with self.assertRaises(ValueError):peel({'a':('','1')},set(),{'a'})
    def test_string_seed_rejected(self):
        with self.assertRaises(ValueError):peel({'a':('0','1')},set(),'a')
    def test_string_anchor_rejected(self):
        with self.assertRaises(ValueError):peel({'a':('0','1')},'0',{'a'})
    def test_input_order_deterministic(self):
        edges={'z':('0','1'),'a':('1','2'),'c':('2','3')}
        self.assertEqual(peel(edges,{'3'},{'z'}),peel(dict(reversed(list(edges.items()))),{'3'},{'z'}))
    def test_seed_at_both_ends_deduplicates(self):
        self.assertEqual(peel({'a':('0','1'),'b':('1','2')},set(),{'a','b'}),['a','b'])
    def test_seed_mid_chain_does_not_guess_a_leaf(self):
        edges={'a':('0','1'),'b':('1','2'),'c':('2','3')}
        self.assertEqual(peel(edges,{'3'},{'b'}),[])
    def test_random_graphs_preserve_all_anchor_connections(self):
        rng=random.Random(314159)
        for _ in range(500):
            count=rng.randint(2,10);nodes=[str(i) for i in range(count)]
            edges={f'e{i}':(nodes[i],nodes[rng.randrange(i)]) for i in range(1,count)}
            for i in range(rng.randrange(5)):
                edges['cross'+str(i)]=tuple(rng.sample(nodes,2))
            anchors=set(rng.sample(nodes,rng.randint(1,count)))
            removed=set(peel(edges,anchors,set(rng.sample(list(edges),rng.randrange(len(edges)+1)))))
            after={k:v for k,v in edges.items() if k not in removed}
            for a in anchors:
                for b in anchors:self.assertEqual(connected(edges,a,b),connected(after,a,b))

if __name__=='__main__':unittest.main(verbosity=2)
