########################################################
# CS136, problem set 2, Peer to Peer client
# Kojin Oshiba, Roman Sigalov
# PropShare client
########################################################

import random
import logging
from messages import Upload, Request
from util import even_split, mean
from peer import Peer

def proportional_split(n, lst):
    ans = []
    if type(n) is not int:
        raise TypeError("n must be int")
    lst_sum = 0
    for i in lst:
        lst_sum += i
    if abs(lst_sum - 100) > 1e-5:
        raise TypeError("lst elements must add up to 100. It's %d", lst)
    ans = []
    last_split = n
    for i in lst[:-1]:
        ith_split = (n*i)//100
        ans.append(ith_split)
        last_split -= ith_split
    ans.append(last_split)
    return ans

class PiratesPropShare(Peer):
    
    def post_init(self):
        print "post_init(): %s here!" % self.id
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
        self.current_opt_unchoke = ""
    
    def requests(self, peers, history):

        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = filter(needed, range(len(self.pieces)))
        np_set = set(needed_pieces) # sets support fast intersection ops.

        requests = []   # We'll put all the things we want here
        
        av_dict = {}
        # Count the number of each available piece.
        for i in np_set:
            av_dict[i] = 0
            for peer in peers:
                if (i in peer.available_pieces):
                    av_dict[i] += 1
    
        # For each peer, find n pieces to request, in order of rearest.
        
        for peer in peers:
            av_dict_tmp = av_dict.copy()
            av_set = set(peer.available_pieces)
            isect = av_set.intersection(np_set)
            n = min(self.max_requests, len(isect))
        
            while n > 0:
                # Find the rearest piece.
                piece_id = min(av_dict_tmp, key = av_dict.get)
                av_dict_tmp.pop(piece_id)
                if piece_id in av_set:
                    start_block = self.pieces[piece_id]
                    r = Request(self.id, peer.id, piece_id, start_block)
                    requests.append(r)
                    n -= 1
                    av_set.remove(piece_id)
                if len(av_set) == 0:
                    break
        return requests
    
    def uploads(self, requests, peers, history):
    
        round = history.current_round()
        logging.debug("%s again.  It's round %d." % (
            self.id, round))
    
        if len(requests) == 0:
            print "aaaaaaaaaaaaa"
            print peers
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:

##################################################################
########## Proportional Unchoking #############################
##################################################################

            bw_share_for_optimistic = 10 #share of its bandwidth for optimistic unchoking in percent
            request_bwd_history = {}
            chosen_bwd = []
            share_lst = []
            chosen = []
            print "Requests, all:"
            print requests
            for request in requests:
                request_bwd_history[request.requester_id] = 0
            # count bwd from the last round for each peer
            if round >= 1:
                for download in history.downloads[round-1]:
                    if download.from_id in request_bwd_history:
                        request_bwd_history[download.from_id] += download.blocks
            # If requester was uploading in the last round, unchoke them.
            for request in requests:
                for peer_id in request_bwd_history:
                    if peer_id == request.requester_id:
                        chosen.append(peer_id)
                        chosen_bwd.append(request_bwd_history[peer_id])
                        break

################################################################
################################################################
########## Implementing proportional optimistic unchoking ######
################################################################

            peers_tmp = peers
            is_opt = False

            if len(peers_tmp) > 0:
                opt_unchoke = random.choice(peers_tmp).id
                chosen.append(opt_unchoke)
                print "New optimistic unchoking " + opt_unchoke
                is_opt = True
            # Calculate the percentage of allocation for each chosen peer
            if is_opt:
                bwd_sum = sum(chosen_bwd)
                last_share = 100
                if bwd_sum > 0:
                    for bwd in chosen_bwd:
                        share = (bwd*(100-bw_share_for_optimistic))//bwd_sum
                        share_lst.append(share)
                        last_share -= share
                share_lst.append(last_share)
                print "is_opt"
                print share_lst
            else:
                bwd_sum = sum(chosen_bwd)
                last_share = 100
                if bwd_sum > 0:
                    for bwd in chosen_bwd[:-1]:
                        share = (bwd*100)//bwd_sum
                        share_lst.append(share)
                        last_share -= share
                share_lst.append(last_share)
                print "isn't_opt"
                print share_lst
#############################################################
            bws = proportional_split(self.up_bw, share_lst)
           
        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]

        return uploads
        