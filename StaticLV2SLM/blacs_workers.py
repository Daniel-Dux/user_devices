from blacs.tab_base_classes import Worker, define_state, MODE_BUFFERED, MODE_MANUAL
import socket

import numpy as np


class StaticLV2SLM_Worker(Worker):
    
    def init(self):
        self.smart_cache = {"coefficient_names": None, "coefficient_values": None}
        
        if not hasattr(self, 'mock'):
            self.mock = False
        if not hasattr(self, 'device_address'):
            self.device_address = '127.0.0.1'
        if not hasattr(self, 'device_port'):
            self.device_port = 65234
            
    def _format_coefficients_json(self, coefficient_names, coefficient_values):
        """Format coefficients as JSON: '["var1", "var2"];[133,-43.001]'"""
        import json
        
        # Convert bytes to strings if necessary
        if coefficient_names.size > 0 and isinstance(coefficient_names[0], bytes):
            names_list = [name.decode('utf-8') for name in coefficient_names]
        else:
            names_list = list(coefficient_names)
        
        # Convert numpy array to native Python types for JSON serialization
        values_list = [float(v) if np.isfinite(v) else None for v in coefficient_values]
        
        names_json = json.dumps(names_list)
        values_json = json.dumps(values_list)

        return f"{names_json};{values_json}"
        
    # def _transmit(self, coefficient_names, coefficient_values):
    #     """Transmit coefficients over TCP (or log in mock mode)."""
    #     json_str = self._format_coefficients_json(coefficient_names, coefficient_values)
        
    #     if self.mock:
    #         self.logger.info(f"Mock transmit: {json_str}")
    #         return
        
    #     # Send over TCP
    #     try:
    #         socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #         socket_conn.connect((self.device_address, self.device_port))
    #         socket_conn.sendall(json_str.encode())
    #         socket_conn.close()
    #     except Exception as e:
    #         self.logger.error(f"Failed to transmit: {e}")
    
    def _transmit(self, coefficient_names, coefficient_values):
        json_str = self._format_coefficients_json(coefficient_names, coefficient_values)

        if self.mock:
            self.logger.info(f"Mock transmit: {json_str}")
            return

        try:
            with socket.create_connection((self.device_address, self.device_port), timeout=3.0) as sock:
                sock.settimeout(3.0)
                sock.sendall(json_str.encode("utf-8"))
                sock.shutdown(socket.SHUT_WR)  # signalisiert: Request komplett gesendet

                reply = sock.recv(16).decode("utf-8", errors="replace").strip()
                if reply not in ("OK", "ER"):
                    self.logger.warning(f"Unexpected SLM reply: {reply!r}")
                elif reply == "ER":
                    self.logger.error("SLM backend returned ER")
        except Exception as e:
            self.logger.error(f"Failed to transmit: {e}")
    
    
    def transition_to_buffered(self, device_name, h5file, initial_values, fresh):
        
        self.hdf5_file = h5file
        
        import h5py
        with h5py.File(h5file, 'r') as f:
            group = f[f"devices/{device_name}"]
            coefficient_names = np.asarray(group['coefficient_names'][:])
            coefficient_values = np.asarray(group['coefficient_values'][:])
        
        if coefficient_names.size == 0:
            self.logger.info("No coefficients in this shot; skipping transmission.")
            self.smart_cache["coefficient_names"] = coefficient_names
            self.smart_cache["coefficient_values"] = coefficient_values
            return initial_values
        
        if coefficient_names.size != coefficient_values.size:
            self.logger.error("Coefficient names and values size mismatch; skipping transmission.")
            self.smart_cache["coefficient_names"] = coefficient_names
            self.smart_cache["coefficient_values"] = coefficient_values
            return initial_values
        
        if fresh or not np.array_equal(coefficient_names[:], self.smart_cache["coefficient_names"]) or not np.array_equal(coefficient_values[:], self.smart_cache["coefficient_values"]):
            self.logger.info("Coefficient change detected; transmitting new values.")
            self._transmit(coefficient_names, coefficient_values)
            self.smart_cache["coefficient_names"] = coefficient_names
            self.smart_cache["coefficient_values"] = coefficient_values
        
        return initial_values
            
        
    def program_manual(self, value):

        return value
    
    def transition_to_manual(self):

        return True
    
    def abort_transition_to_buffered(self):
        
        return True
    
    def abort_buffered(self):
        
        return True
    
    def reset(self):
        
        return True