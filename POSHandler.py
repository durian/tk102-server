#!/usr/bin/python
# -*- coding: utf-8 -*-
#
from smtplib import SMTP
from email.MIMEText import MIMEText
from email.Header import Header
from email.Utils import parseaddr, formataddr
from email.mime.multipart import MIMEMultipart
from email.encoders import encode_7or8bit

class POSHandler():
    def __init__(self, obj):
    	self.obj = obj

    def on_start(self):
        """
        Called when a new tracker is initialized.
        """
        #send_email("sender@invalid.com", "receiver@invalid.com", "Tracker", "Tracker started")
        pass

    def on_finish(self):
        """
        Called before the thread exits.
        """
        pass

    def on_exit(self, imei):
        """
        Called after the thread exits/has been killed
        """
        pass

    def on_info(self, msg):
        """
        Called when message other than "tracker" has been received.
        """
        pass

    def on_position(self):
        """
        Called everytime we receive a GPS position string.
        """
        #obj.info( repr(obj.pos) )
        pass

    def on_stationary(self):
        """
        Called if last two positions are the same.
        """
        pass

    def on_start_move(self):
        """
        Called if moving again after stationary destection.
        """
        pass

def send_email(sender, recipient, subject, body ):
    SMTPHOST = "HOST"
    SMTPPORT = 25
    SMTPUSER = "USER"
    SMTPPASS = "PASS"

    header_charset = 'UTF-8' 

    # We must choose the body charset manually
    for body_charset in 'UTF-8', 'US-ASCII', 'ISO-8859-1', 'UTF-8':
        try:
            body.encode(body_charset)
        except UnicodeError:
            pass
        else:
            break

    # Split real name (which is optional) and email address parts
    sender_name, sender_addr       = parseaddr(sender)
    recipient_name, recipient_addr = parseaddr(recipient)

    # We must always pass Unicode strings to Header, otherwise it will
    # use RFC 2047 encoding even on plain ASCII strings.
    sender_name    = str(Header(unicode(sender_name), header_charset))
    recipient_name = str(Header(unicode(recipient_name), header_charset))

    # Make sure email addresses do not contain non-ASCII characters
    sender_addr    = sender_addr.encode('ascii')
    recipient_addr = recipient_addr.encode('ascii')

    # Create the message ('plain' stands for Content-Type: text/plain)
    msg = MIMEText(body.encode(body_charset), 'plain', body_charset)

    msg['From']    = formataddr((sender_name, sender_addr))
    msg['To']      = formataddr((recipient_name, recipient_addr))
    msg['Subject'] = Header(unicode(subject), header_charset)

    smtp = SMTP(SMTPHOST, SMTPPORT) 
    smtp.login(SMTPUSER, SMTPPASS)
    smtp.sendmail(sender, recipient, msg.as_string())
    '''
    smtp = SMTP('smtp.gmail.com',587) #port 465 or 587
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo
    smtp.login("USER@gmail.com", "PASS")
    smtp.sendmail(sender, recipient, msg.as_string())
    smtp.close()
    '''
