# Runs randomized staking transactions and makes some basic checks on the final `staked` values
# TODO: presently this test fails with a node crash. Once that is fixed, asserts that validate proper stakes need to be introduced
# TODO: the current expected stakes are not correctly computed

import sys, time, base58, random

sys.path.append('lib')

from cluster import start_cluster
from transaction import sign_staking_tx

TIMEOUT = 150

all_stakes = []
next_nonce = 3

# other tests can set `sequence` to some sequence of triplets of stakes
# `do_moar_stakes` first uses the elements of `sequence` for stakes before switching to
# random. See `staking_repro1.py` for an example
sequence = []

def get_validators():
    return set([x['account_id'] for x in nodes[0].get_status()['validators']])

def get_stakes():
    return [int(nodes[2].get_account("test%s" % i)['result']['staked']) for i in range(3)]

def get_expected_stakes():
    global all_stakes
    return [max([x[i] for x in all_stakes[-4:]]) for i in range(3)]

def do_moar_stakes(last_block_hash):
    global next_nonce, all_stakes, sequence

    if len(sequence) == 0:
        stakes = [0, 0, 0]
        # have 1-2 validators with stake, and the remaining without
        stakes[random.randint(0, 2)] = random.randint(70000000000000000000000000, 100000000000000000000000000)
        stakes[random.randint(0, 2)] = random.randint(70000000000000000000000000, 100000000000000000000000000)
    else:
        stakes = sequence[0]
        sequence = sequence[1:]

    vals = get_validators()
    val_id = int(list(vals)[0][4:])
    for i in range(3):
        tx = sign_staking_tx(nodes[i].signer_key, nodes[i].validator_key, stakes[i], next_nonce, base58.b58decode(last_block_hash.encode('utf8')))
        nodes[val_id].send_tx(tx)
        next_nonce += 1

    all_stakes.append(stakes)
    print("")
    print("Sent staking txs: %s" % stakes)


def doit(seq = []):
    global nodes, all_stakes, sequence
    sequence = seq

    config = {'local': True, 'near_root': '../target/debug/'}
    nodes = start_cluster(2, 1, 1, config, [["epoch_length", 5], ["validator_kickout_threshold", 40]], {2: {"tracked_shards": [0]}})

    started = time.time()

    status = nodes[2].get_status()
    height = status['sync_info']['latest_block_height']
    hash_ = status['sync_info']['latest_block_hash']

    print("Initial stakes: %s" % get_stakes())
    all_stakes.append(get_stakes())

    do_moar_stakes(hash_)
    last_staked_height = height
        
    while True:
        assert time.time() - started < TIMEOUT

        status = nodes[0].get_status()
        height = status['sync_info']['latest_block_height']
        hash_ = status['sync_info']['latest_block_hash']

        if (height + 2) // 5 != (last_staked_height + 2) // 5:
            print("Current stakes: %s" % get_stakes())
            if len(all_stakes) > 1:
                print("Expect  stakes: %s" % get_expected_stakes())
            do_moar_stakes(hash_)
            last_staked_height = height

if __name__ == "__main__":
    doit()
