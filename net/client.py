# =================
# Solex - client.py
# =================

# System.
from sys import exit
from glob import glob
from os import path as os_path

# Panda3d.
from direct.showbase.ShowBase import ShowBase
from panda3d.core import ClockObject, Filename

# Local.
from etc.settings import _path, _sim
from etc.shiva import Shiva_Compiler as SC
from etc.util import Throttle
from gui.ueh import Default_UEH
from solex.environments import *
from solex.bodies import *
from solex.simulator import Simulator


class Client(ShowBase):
    
    # Public.
    def init_system(self, sys_name):
        if self.SYS and self.SYS.name == sys_name: return
        sys_recipe = self.sys_recipes[sys_name]
        self.SYS = self.__init_Sys(sys_recipe)
        self.SIM.init_system(sys_recipe)
        self.PRE_VIEW.on_sys_init(self.SYS)
        self.ENV.on_sys_init(self.SYS)
        self.SIM.start()
    def switch_display(self, display):
        self.__switch_Display(display)
    def refresh_servers(self):
        self.servers = self.__refresh_Servers()
    def refresh_sys_recipes(self):
        self.sys_recipes = self.__refresh_Sys_Recipes()
        
    # Protected.
    def _exit(self):
        self.SIM.stop()
        exit()
    
    # Setup.
    def __init__(self):
        ShowBase.__init__(self)
        self.Clock = ClockObject.getGlobalClock()
        self._alive = True
        self._connected = False
        self._prev_t = 0
        self._display_region = self.cam.getNode(0).getDisplayRegion(0)
    
        # Main menu and environment.
        self.LOBBY = Lobby(self)  # <-
        self.ENV = Environment(self)  # <-
        self.PRE_VIEW = Pre_View(self)  # <-
        self.DISPLAY = self.LOBBY
        self.SYS = None
        self.SIM = Simulator(_sim.MAX_LOCAL_BODIES)
        self.servers = []
        self.sys_recipes = self.__refresh_Sys_Recipes()
        
        # Player and main objects.
        ## self.PLAYER = Player()  # <-
        self.UEH = Default_UEH()  # <-
        
        self.setBackgroundColor(0,0,0)
        self.disableMouse()
        
        # Network.
        '''self.host = socket.gethostbyname(socket.gethostname())
        self.tcp_addr = (self.host, CLIENT_TCP_PORT)
        self.udp_addr = (self.host, CLIENT_UDP_PORT)
        ## self.tcp_req_addr = (self.host, CLIENT_REQUEST_PORT)
        self.proxy_tcp_addr = None   ## self.client_proxy_tcp_addr'''

        # Main loop.
        taskMgr.add(self._main_loop_, "main_loop", appendTask=True, sort=0)  # <-
        taskMgr.doMethodLater(1/_sim.HZ, self._state_, "state_loop")
        
    
    def _main_loop_(self, task):
        # Get 'dt' - time lapsed since last frame.
        new_t = self.Clock.getRealTime()
        dt = new_t - self._prev_t
        
        # User events.
        ue = self.UEH._get_events_()  # <-
        self._handle_user_events_(ue, dt)  # <-
        
        # Main loops.
        self.DISPLAY._main_loop_(ue, dt)  # <-
        self._prev_t = new_t
        
        if self._alive: return task.cont
        else: self._exit()

    def _handle_user_events_(self, ue, dt):
        pass
    def _state_(self, task):
        if self.SIM.alive.value:
            state = self.SIM.get_state(self.ENV.CAMERA.sys_pos)
            live_ids = set(self.ENV.live_object_ids)
            for obj_id, obj_state in state.items():
                obj = self.SYS.OBJECT_DICT[obj_id]
                obj.sys_pos.set(*obj_state['sys_pos'])
                obj.sys_vec.set(*obj_state['sys_vec'])
                obj.sys_hpr.set(*obj_state['sys_hpr'])
                obj.sys_rot.set(*obj_state['sys_rot'])
                print(obj_id, obj.sys_pos, obj.MODEL_NP.getPos(render))
                if obj_id not in live_ids:
                    self.ENV.add_object(obj_id, obj)
                else:
                    live_ids.remove(obj_id)
            print()
            # Remove superfluous objects.
            for obj_id in live_ids:
                obj = self.SYS.OBJECT_DICT[obj_id]
                self.ENV.remove_object(obj_id, obj)
                
        return task.again

    def __refresh_Sys_Recipes(self):
        sys_dir_path = Filename("{}/*.shv".format(_path.SYSTEMS))
        sys_files = glob(sys_dir_path.toOsLongName())
        sys_recipes = {}
        for sys_file in sys_files:
            base_name = os_path.basename(sys_file)
            sys_name = os_path.splitext(base_name)[0]
            sys_recipes[sys_name] = SC.compile_sys_recipe(sys_file)
        return sys_recipes

    def __refresh_Servers(self):
        server_array = []
        for host in SERVER_LIST:
            server_addr = (host, SERVER_PING_PORT)
            with TCP_Ping(server_addr) as tcp:
                tcp.ping()
            if tcp.val < 0: sys_name, ping = "-", "-"
            else: sys_name, ping = tcp.msg, tcp.val
            server_array.append([host, "-", sys_name, str(ping)])
        return server_array
        
    def __init_Sys(self, sys_recipe):  ## move to System in bodies.
        sys = System(sys_recipe)
        
        def add_body(body_recipe):
            body = Body(body_recipe)
            sys.BODIES.append(body)
            if body.__class__.__name__ == "Star":
                sys.STARS.append(body)
            sys.OBJECT_DICT[body_recipe['name']] = body
            for sat_recipe in body_recipe['sats']:
                sat = add_body(sat_recipe)
                body.SATS.append(sat)
            return body
            
        sys.root = add_body(sys_recipe)
        return sys

    def __switch_Display(self, display):
        self.DISPLAY.NP.hide()
        self.DISPLAY.GUI.NP.hide()
        self.DISPLAY.CAMERA.cam_node.setActive(False)
        display.NP.show()
        display.GUI.NP.show()
        display.CAMERA.cam_node.setActive(True)
        self._display_region.setCamera(display.CAMERA.NP)
        self.DISPLAY = display



