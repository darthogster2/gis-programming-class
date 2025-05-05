# -*- coding: utf-8 -*-
def classFactory(iface):
    from .tselovalnikov import Tselovalnikov
    return Tselovalnikov(iface)
