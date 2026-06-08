package pl.distributed.zkwatcher;

import org.apache.zookeeper.ZooKeeper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import pl.distributed.zkwatcher.config.AppConfig;
import pl.distributed.zkwatcher.process.DockerProcessLauncher;
import pl.distributed.zkwatcher.process.ExternalAppLauncher;
import pl.distributed.zkwatcher.process.ProcessManager;
import pl.distributed.zkwatcher.web.EventBroadcaster;
import pl.distributed.zkwatcher.web.WebServer;
import pl.distributed.zkwatcher.zk.NodeAWatcher;

public final class WatcherApp {

    private static final Logger log = LoggerFactory.getLogger(WatcherApp.class);

    private WatcherApp() {
    }

    public static void main(String[] args) throws Exception {
        AppConfig config = AppConfig.fromArgs(args);
        log.info("Starting ZooKeeper Watcher Application");
        log.info("ZK connect: {}, root: {}, HTTP port: {}, external mode: {}",
                config.getZkConnectString(),
                config.getZkRootPath(),
                config.getHttpPort(),
                config.getExternalAppMode());

        EventBroadcaster broadcaster = new EventBroadcaster();
        ExternalAppLauncher externalAppLauncher = createLauncher(config);
        NodeAWatcher nodeAWatcher = new NodeAWatcher();

        WebServer webServer = new WebServer(config.getHttpPort(), broadcaster, nodeAWatcher::getAppState);
        webServer.start();

        ZooKeeper zooKeeper = new ZooKeeper(
                config.getZkConnectString(),
                config.getSessionTimeoutMs(),
                nodeAWatcher
        );
        nodeAWatcher.init(zooKeeper, config.getZkRootPath(), externalAppLauncher, broadcaster);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                log.info("Shutting down...");
                webServer.stop();
                if (externalAppLauncher.isRunning()) {
                    externalAppLauncher.stop();
                }
                zooKeeper.close();
            } catch (Exception e) {
                log.warn("Shutdown error: {}", e.getMessage());
            }
        }));

        nodeAWatcher.awaitConnection();
        log.info("Connected to ZooKeeper ensemble");
        nodeAWatcher.syncInitialState();
        broadcaster.broadcastState(nodeAWatcher.getAppState());

        Thread.currentThread().join();
    }

    private static ExternalAppLauncher createLauncher(AppConfig config) {
        return switch (config.getExternalAppMode()) {
            case PROCESS -> new ProcessManager(config.getExternalAppCommand());
            case DOCKER -> new DockerProcessLauncher(config.getExternalDockerContainer());
        };
    }
}
