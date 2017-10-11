from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3

class TunnelVXLAN(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TunnelVXLAN, self).__init__(*args, **kwargs)
        # initialize mac address table.


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        type_eth  = (ofproto.OFPHTN_ONF << 16) | ofproto.OFPHTO_ETHERNET
        type_ip   = (ofproto.OFPHTN_ETHERTYPE << 16) | 0x0800
        type_udp   = (ofproto.OFPHTN_IP_PROTO << 16) | 17
        type_vxl  = (ofproto.OFPHTN_UDP_TCP_PORT << 16) | 4789
        type_next = (ofproto.OFPHTN_ONF << 16) | ofproto.OFPHTO_USE_NEXT_PROTO

        # install the table-miss flow entry.

        # Encap Flow
        match = parser.OFPMatch(in_port=1, eth_type=2048)
        actions = [
                   # encap VXLAN
                   parser.OFPActionEncap(type_vxl),
                   parser.OFPActionSetField(vxlan_vni=1),
                   parser.OFPActionEncap(type_udp),
                   parser.OFPActionSetField(udp_src=5432),
                   parser.OFPActionSetField(udp_dst=4789),
                   parser.OFPActionEncap(type_ip),
                   parser.OFPActionSetField(ipv4_src='10.0.0.1'),
                   parser.OFPActionSetField(ipv4_dst='172.21.0.2'),
                   parser.OFPActionSetNwTtl(nw_ttl=64),
                   parser.OFPActionEncap(type_eth),
                   parser.OFPActionSetField(eth_src='12:22:22:22:22:22'),
                   parser.OFPActionSetField(eth_dst='22:33:33:33:33:33'),
                   # output
                   parser.OFPActionOutput(2, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

        # Decap Flow
        match = parser.OFPMatch(in_port=2, eth_type=2048, ip_proto=17, udp_dst=4789)
        actions = [
                   # decap VXLAN
                   parser.OFPActionDecap(type_eth, type_ip),
                   parser.OFPActionDecap(type_ip, type_udp),
                   parser.OFPActionDecap(type_udp, type_vxl),
                   parser.OFPActionDecap(type_vxl, type_next),
                   # output
                   parser.OFPActionOutput(1, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

