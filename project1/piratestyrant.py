########################################################
# CS136, problem set 2, Peer to Peer client
# Kojin Oshiba, Roman Sigalov
# BitTyrant client
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

class PiratesTyrant3(Peer):
    def post_init(self):
        print "post_init(): %s here!" % self.id
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
        self.downloadRate = {}
        self.uploadRate = {}
        self.slots = {}
        self.downloadUploadRatio = {}
        self.bandwidthHistory = []

    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see
        returns: a list of Request() objects
        This will be called after update_pieces() with the most recent state.
        """
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = filter(needed, range(len(self.pieces)))
        np_set = set(needed_pieces) # sets support fast intersection ops.
        
        requests = []   # We'll put all the things we want here
        
        av_dict = {}
        for i in np_set:
            av_dict[i] = 0
            for peer in peers:
                if (i in peer.available_pieces):
                    av_dict[i] += 1
        
        for peer in peers:
            av_dict_tmp = av_dict.copy()
            av_set = set(peer.available_pieces)
            isect = av_set.intersection(np_set)
            n = min(self.max_requests, len(isect))
    
            """    if piece_id in av_set:"""
    
            while n > 0:
                piece_id = min(av_dict_tmp, key = av_dict.get)
                av_dict_tmp.pop(piece_id)
                if piece_id in av_set:
                    start_block = self.pieces[piece_id]
                    r = Request(self.id, peer.id, piece_id, start_block)
                    requests.append(r)
                    n -= 1
                if len(av_set) == 0:
                    break
        
        return requests
    
    def uploads(self, requests, peers, history):
        
        ##################################################################
        ########### updating d_js ########################################
        ##################################################################
        alpha = 0.2
        gamma = 0.1
        round = history.current_round()
        self.bandwidthHistory.append(self.up_bw)
        
        if round == 0:
            bw_list = even_split(self.up_bw,len(peers))
            for peer,i in zip(peers,range(len(peers))):
                self.downloadRate[peer.id] = (self.conf.max_up_bw - self.conf.min_up_bw)/(4*2)
                if bw_list[i] == 0:
                    self.uploadRate[peer.id] = 0.5
                else:
                    self.uploadRate[peer.id] = bw_list[i]
                self.slots[peer.id] = 4
                self.downloadUploadRatio[peer.id] = 1
        
        else:
            for peer in peers:
                self.downloadRate[peer.id] = 0
                for download in history.downloads[round-1]:
                    if peer.id == download.from_id:
                        self.downloadRate[peer.id] += download.blocks
                        
                        if download.blocks == 0: print "!!!!!! %s uploaded %s block(s)" % (peer.id, download.blocks)
                        self.slots[peer.id] = mean(self.bandwidthHistory)/float(self.downloadRate[peer.id]) # Find how to find out max and min bw or infer from personal history
                        
                        if round >= 3:
                            peer_download = 0
                            
                            for download2 in history.downloads[round-2]:
                                if peer.id == download2.from_id:
                                    
                                    for download3 in history.downloads[round-3]:
                                        if peer.id == download3.from_id:
                                            peer_download += 1
                            if peer_download > 0:
                                self.uploadRate[peer.id] *= 1 - gamma
                        break
                    
                    if len(peer.available_pieces) > 0:
                        av_pieces = float(len(peer.available_pieces))
                        rnd = float(round)
                        slots = float(self.slots[peer.id])
                        self.downloadRate[peer.id] = av_pieces/(rnd * self.conf.blocks_per_piece * slots)
                        self.uploadRate[peer.id] *= 1 + alpha

                self.downloadUploadRatio[peer.id] =  self.downloadRate[peer.id]/self.uploadRate[peer.id]
        
        
        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
            uploads = []
        else:
            logging.debug("Still here: uploading to a random peer")
            # change my internal state for no reason
            self.dummy_state["cake"] = "pie"
        
        ##################################################################
        ########### Building upload list #################################
        ##################################################################
        
            sumUpload = 0
            chosen = {}
            downloadUploadRatio_tmp = {}
            
            # creating list with ratios for only peers in requests
            for request in requests:
                downloadUploadRatio_tmp[request.requester_id] = self.downloadUploadRatio[request.requester_id]
            while (sumUpload <= self.up_bw and len(downloadUploadRatio_tmp) > 0):
                peer_id = max(downloadUploadRatio_tmp, key = downloadUploadRatio_tmp.get)
                chosen[peer_id] = downloadUploadRatio_tmp.pop(peer_id)
                sumUpload += self.uploadRate[peer_id]
            
            """ Calculate the total proportional BW allocated to other peers """
            
            totalUploadBW = 0
            
            for choice in chosen:
                totalUploadBW += chosen[choice]
            
            """ Make each BW as a proportion of totalUploadBW """
            
            if float(totalUploadBW) == 0:
                uploads = []
            else:
                for choice in chosen:
                    chosen[choice] = 100 * float(chosen[choice]) / float(totalUploadBW)
            
                """ Now need to divide our BW as integers according to chosen vector """
                peerWeights = [value for (key, value) in sorted(chosen.items())]
                peerNames = sorted(chosen)
                
                bws = proportional_split(self.up_bw, peerWeights)
                
                # create actual uploads out of the list of peer ids and bandwidths
                uploads = [Upload(self.id, peer_id, bw)
                    for (peer_id, bw) in zip(chosen, bws)]
        
        return uploads






