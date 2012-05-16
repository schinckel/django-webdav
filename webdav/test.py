import util
xml = "<note><to>Tove</to><from>Jani</from><heading>Reminder</heading><body>Don't forget me this weekend!</body></note>"
e = util.Elem.from_xml(xml)
print e, e.children
print e.get_xml()
