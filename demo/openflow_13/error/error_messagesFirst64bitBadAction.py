"""
<title>First64bitBadAction</title>
<description>
   The reply of the error should contain the fist 64 bit of the invalid message 
</description>
"""

try:
    if('TWISTER_ENV' in globals()):
        from ce_libs.openflow.of_13.openflow_base import *
        testbed=currentTB
        from ce_libs import ra_proxy
        ra_service=ra_proxy                        
except:
    raise

class First64bitBadAction(SimpleDataPlane):
    """
    Verify error reply contains 64bit
    """
    def runTest(self):
        self.logger.info("Running BadGroupID test")
        of_ports = self.port_map.keys()
        of_ports.sort()
        self.assertTrue(len(of_ports) > 0, "Not enough ports for test")

        act = action.action_group()
        self.logger.info("Clear the switch state, delete all flows")
        rv = testutils.delete_all_flows(self.controller, self.logger)
        self.assertEqual(rv, 0, "Failed to delete all flows")

        request = message.flow_mod()
        request.buffer_id = 0xffffffff
        act.group_id = ofp.OFPG_MAX
        inst = instruction.instruction_apply_actions()
        inst.actions.add(act)
        request.instructions.add(inst)

        self.logger.info("Inserting flow")
        logMsg('logDebug',"Request send to switch:")
        logMsg('logDebug',request.show())
        rv = self.controller.message_send(request)
        self.assertTrue(rv != -1, "Error installing flow mod")
        (response, pkt) = self.controller.poll(exp_msg=ofp.OFPT_ERROR,
                                               timeout=5)
        self.assertTrue(response is not None,
                                'Switch did not reply with error messge')
        logMsg('logDebug',"Response from switch:")
        logMsg('logDebug',response.show())
        self.assertTrue(response.type==ofp.OFPET_BAD_ACTION,
                               'Error type is not OFPET_BAD_ACTION')
        self.assertTrue(response.code==ofp.OFPBAC_BAD_OUT_GROUP,
                               'Error code is not OFPBAC_BAD_OUT_GROUP')
	self.assertTrue(len(response.data) > 64, 'Reply data is not 64bit')
	
tc = First64bitBadAction()
_RESULT = tc.run()