########################################################
# CS136, problem set 2, Peer to Peer client
# Kojin Oshiba, Roman Sigalov
# Tournament Client
########################################################

import random
import logging
import math

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

class PiratesTourney4(Peer):
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

        rarests = []
        requests = []   # We'll put all the things we want here

        for peer in peers:
            len(peer.available_pieces)

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
            mx = max(self.max_requests, len(isect))
            mn = min(self.max_requests, len(isect))
            rarest_count = mn
            """    if piece_id in av_set:"""
            if mx == len(isect):
                while rarest_count > 0 and mx-(mn-rarest_count) >= mn:
                    piece_id = min(av_dict_tmp, key = av_dict_tmp.get)
                    av_dict_tmp.pop(piece_id)
                    if piece_id in av_set:
                        start_block = self.pieces[piece_id]
                        r = Request(self.id, peer.id, piece_id, start_block)
                        rarests.append(r)
                        rarest_count -= 1
                    if len(av_set) == 0:
                        break
                request_count = mx - len(rarests)
                while request_count > 0:
                    piece_id = min(av_dict_tmp, key = av_dict_tmp.get)
                    av_dict_tmp.pop(piece_id)
                    if piece_id in av_set:
                        start_block = self.pieces[piece_id]
                        r = Request(self.id, peer.id, piece_id, start_block)
                        requests.append(r)
                        request_count -= 1
                    if len(av_set) == 0:
                        break
            else:
                mn_tmp = mn
                while mn_tmp > 0:
                    piece_id = min(av_dict_tmp, key = av_dict.get)
                    av_dict_tmp.pop(piece_id)
                    if piece_id in av_set:
                        start_block = self.pieces[piece_id]
                        r = Request(self.id, peer.id, piece_id, start_block)
                        requests.append(r)
                        mn_tmp -= 1
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
                self.downloadRate[peer.id] = 1
                if bw_list[i] == 0:
                    self.uploadRate[peer.id] = 0.5
                else:
                    self.uploadRate[peer.id] = bw_list[i]
                self.slots[peer.id] = 4
                self.downloadUploadRatio[peer.id] = 1
        else:
            for peer in peers:
                for download in history.downloads[round-1]:
                    if peer.id == download.from_id:
                        self.downloadRate[peer.id] = download.blocks
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
        
        logging.debug("%s again.  It's round %d." % (
            self.id, round))

        ########### Dynamic Optimistic Unchoking #################################
        ########### Eallocate each 3 rounds ######################################

        ### Choose peer to uchoke every 3 round
        ### Choose # of peers divided by x:
        
        x = 3
        if round % 3 ==0:
            self.optUnchokedPeers = random.sample(peers, len(peers)/x)

        ### Initial share to uchoke:
        a = 0.5

        availPiecesShare = float(sum(self.pieces))/float(self.conf.num_pieces*self.conf.blocks_per_piece)
        ### Allocate BW to opt unchoking
        bwToOptUnchoking = (a*self.up_bw - availPiecesShare * self.up_bw * a) + 0.001
        ### Divide this BW among number of neighbors divided by x
        bwToOptUnchoking = bwToOptUnchoking/(len(peers)/x)
        
        optUnchokedAllocation = {}


        for peer in self.optUnchokedPeers:
            optUnchokedAllocation[peer.id] = float(100 * bwToOptUnchoking) /(float((a*self.up_bw - availPiecesShare * self.up_bw * a)) +0.001)

        up_bw_available = self.up_bw - bwToOptUnchoking*(len(peers)/x)


        # Removing optimistically unchoked peers from consideration
        peers_tmp = list(peers)
        for peer in self.optUnchokedPeers:
            if peer in peers_tmp:
                peers_tmp.remove(peer)

        #########################################################################
        ########### Building upload list ########################################
        #########################################################################


        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
            uploads = []
        else:
            sumUpload = 0
            chosen = {}
            downloadUploadRatio_tmp = {}
            
            # creating list with ratios for only peers in requests

            for request in requests:
                for peer in peers_tmp:
                    if request.requester_id == peer.id:
                        downloadUploadRatio_tmp[request.requester_id] = self.downloadUploadRatio[request.requester_id]


            for key in downloadUploadRatio_tmp:
                if downloadUploadRatio_tmp[key] in self.optUnchokedPeers:
                    downloadUploadRatio_tmp.pop(key)
            
            needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
            needed_pieces = filter(needed, range(len(self.pieces)))
            
            while (sumUpload <= up_bw_available * 0.75 and len(downloadUploadRatio_tmp) > 0):
                peer_id = max(downloadUploadRatio_tmp, key = downloadUploadRatio_tmp.get)
                chosen[peer_id] = downloadUploadRatio_tmp.pop(peer_id)
                sumUpload += self.uploadRate[peer_id]

            """ Calculate the total proportional BW allocated to other peers """
            
            totalUploadBW = 0
            for choice in chosen:
                totalUploadBW += chosen[choice]
            
            """ Make each BW as a proportion of totalUploadBW """

            if (float(totalUploadBW) * len(optUnchokedAllocation) == 0):
                uploads = []
            else:
                for choice in chosen:
                    chosen[choice] = 100 * float(chosen[choice]) / float(totalUploadBW)

                ### Connecting optimistic unchoking list to tyrant list
                
                """ Now need to divide our BW as integers according to chosen vector """
                
                peerWeights = [value for (key, value) in sorted(chosen.items())]
                peerNames = sorted(chosen)

                bws = proportional_split(int(math.floor(up_bw_available)), peerWeights)

                # create actual uploads out of the list of peer ids and bandwidths
                uploads = [Upload(self.id, peer_id, bw)
                    for (peer_id, bw) in zip(chosen, bws)]

                peerWeights = [value for (key, value) in sorted(optUnchokedAllocation.items())]
                peerNames = sorted(optUnchokedAllocation)
                bws = proportional_split(self.up_bw - int(up_bw_available), peerWeights)

                uploads2 = [Upload(self.id, peer_id, bw)
                    for (peer_id, bw) in zip(peerNames, bws)]

                uploads = uploads + uploads2

                if (round + 1) % 5 == 0:
                    request = random.choice(requests)
                    chosen = [request.requester_id]
                    # Evenly "split" my upload bandwidth among the one chosen requester
                    bws = even_split(self.up_bw, len(chosen))
            
        return uploads







