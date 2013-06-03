#!/usr/bin/python
# -*- coding: utf-8 -*-
#
class POSHandler():
    def __init__(self, obj):
    	self.obj = obj

    def on_start(self, obj):
        """
        Called when a new tracker is initialized.
        """
        print 'send_email("sender@invalid.com", "receiver@invalid.com", "Tracker", "Tracker started");'
        obj.info( repr(obj.pos) )
        pass

    def on_finish(self, obj):
        """
        Called before the thread exits.
        """
        pass

    def on_position(self, obj):
        """
        Called everytime we receive a GPS position string.
        """
        obj.info( repr(obj.pos) )

    def on_stationary(self, obj):
        """
        Called if last two positions are the same.
        """
        pass

    def on_start_move(self, obj):
        """
        Called if moving again after stationary destection.
        """
        pass

