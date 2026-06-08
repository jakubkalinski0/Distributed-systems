package pl.distributed.zkwatcher.web;

import com.google.gson.Gson;
import io.javalin.websocket.WsContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import pl.distributed.zkwatcher.model.AppState;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public class EventBroadcaster {

    private static final Logger log = LoggerFactory.getLogger(EventBroadcaster.class);
    private static final Gson GSON = new Gson();

    private final Set<WsContext> clients = ConcurrentHashMap.newKeySet();

    public void register(WsContext ctx) {
        clients.add(ctx);
        log.info("WebSocket client connected (total={})", clients.size());
    }

    public void unregister(WsContext ctx) {
        clients.remove(ctx);
        log.info("WebSocket client disconnected (total={})", clients.size());
    }

    public void broadcastState(AppState state) {
        broadcast(Map.of(
                "type", "state",
                "payload", state
        ));
    }

    public void broadcastNotification(String message, int childCount) {
        broadcast(Map.of(
                "type", "notification",
                "message", message,
                "childCount", childCount
        ));
    }

    public void broadcastLog(String message) {
        broadcast(Map.of(
                "type", "log",
                "message", message
        ));
    }

    private void broadcast(Map<String, Object> event) {
        String json = GSON.toJson(event);
        for (WsContext client : clients) {
            try {
                client.send(json);
            } catch (Exception e) {
                log.warn("Failed to send WebSocket message: {}", e.getMessage());
                clients.remove(client);
            }
        }
    }
}
