// Scope this DNS pin to Paperclip's CLI process; preserve TLS hostname checks.
import dns from "node:dns";
import { isIP } from "node:net";
import { syncBuiltinESMExports } from "node:module";

const hostname = "pm-haofengmac-mini.taile41bfa.ts.net";
const address = process.env.PAPERCLIP_TAILNET_ADDRESS ?? "100.101.186.83";
if (isIP(address) !== 4) throw new Error("Paperclip requires a valid tailnet IPv4 address.");
const originalLookup = dns.lookup;

dns.lookup = function lookup(host, options, callback) {
  if (String(host).toLowerCase().replace(/\.$/, "") !== hostname) {
    return originalLookup.call(dns, host, options, callback);
  }
  if (typeof options === "function") {
    callback = options;
    options = {};
  }
  if (typeof callback !== "function") throw new TypeError("DNS callback is required.");
  queueMicrotask(() => {
    if (options && typeof options === "object" && options.all) {
      callback(null, [{ address, family: 4 }]);
    } else {
      callback(null, address, 4);
    }
  });
};
syncBuiltinESMExports();
