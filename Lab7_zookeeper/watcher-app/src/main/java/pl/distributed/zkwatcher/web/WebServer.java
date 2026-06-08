package pl.distributed.zkwatcher.web;

import io.javalin.Javalin;
import io.javalin.http.staticfiles.Location;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import pl.distributed.zkwatcher.model.AppState;

import java.time.Duration;
import java.util.function.Supplier;

public class WebServer {

    private static final Logger log = LoggerFactory.getLogger(WebServer.class);

    private final int port;
    private final EventBroadcaster broadcaster;
    private final Supplier<AppState> stateSupplier;
    private Javalin app;

    public WebServer(int port, EventBroadcaster broadcaster, Supplier<AppState> stateSupplier) {
        this.port = port;
        this.broadcaster = broadcaster;
        this.stateSupplier = stateSupplier;
    }

    public void start() {
        app = Javalin.create(config -> {
            config.staticFiles.add(staticFiles -> {
                staticFiles.hostedPath = "/";
                staticFiles.directory = "static";
                staticFiles.location = Location.CLASSPATH;
            });
            config.jetty.modifyWebSocketServletFactory(factory ->
                    factory.setIdleTimeout(Duration.ofHours(1)));
        });

        app.get("/api/state", ctx -> ctx.json(stateSupplier.get()));
        app.ws("/ws", ws -> {
            ws.onConnect(broadcaster::register);
            ws.onClose(broadcaster::unregister);
            ws.onConnect(ctx -> broadcaster.broadcastState(stateSupplier.get()));
        });

        app.start(port);
        log.info("Web GUI available at http://localhost:{}", port);
    }

    public void stop() {
        if (app != null) {
            app.stop();
        }
    }
}
