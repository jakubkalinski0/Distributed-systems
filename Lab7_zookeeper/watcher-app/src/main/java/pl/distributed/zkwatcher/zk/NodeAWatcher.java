package pl.distributed.zkwatcher.zk;

import org.apache.zookeeper.AddWatchMode;
import org.apache.zookeeper.KeeperException;
import org.apache.zookeeper.WatchedEvent;
import org.apache.zookeeper.Watcher;
import org.apache.zookeeper.ZooKeeper;
import org.apache.zookeeper.data.Stat;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import pl.distributed.zkwatcher.model.AppState;
import pl.distributed.zkwatcher.model.TreeNode;
import pl.distributed.zkwatcher.process.ExternalAppLauncher;
import pl.distributed.zkwatcher.web.EventBroadcaster;

import java.util.List;

public class NodeAWatcher implements Watcher {

    private static final Logger log = LoggerFactory.getLogger(NodeAWatcher.class);

    private ZooKeeper zk;
    private String rootPath;
    private ExternalAppLauncher externalAppLauncher;
    private EventBroadcaster broadcaster;
    private final TreeBuilder treeBuilder = new TreeBuilder();

    private volatile String connectionState = "DISCONNECTED";
    private volatile boolean nodeAExists;
    private volatile int childCount;
    private volatile int lastKnownDescendantCount = -1;
    private volatile TreeNode tree;

    public void init(
            ZooKeeper zk,
            String rootPath,
            ExternalAppLauncher externalAppLauncher,
            EventBroadcaster broadcaster) {
        this.zk = zk;
        this.rootPath = rootPath;
        this.externalAppLauncher = externalAppLauncher;
        this.broadcaster = broadcaster;
    }

    public void awaitConnection() throws InterruptedException {
        while (zk.getState() != ZooKeeper.States.CONNECTED) {
            Thread.sleep(100);
        }
        connectionState = "CONNECTED";
    }

    public void syncInitialState() throws KeeperException, InterruptedException {
        syncState();
    }

    @Override
    public void process(WatchedEvent event) {
        Event.KeeperState state = event.getState();
        Event.EventType type = event.getType();
        String path = event.getPath();

        log.info("ZK event: state={}, type={}, path={}", state, type, path);

        if (state == Watcher.Event.KeeperState.SyncConnected && type == Watcher.Event.EventType.None) {
            connectionState = "CONNECTED";
            try {
                syncState();
            } catch (Exception e) {
                log.error("Failed to sync state after reconnect", e);
                broadcaster.broadcastLog("Reconnect sync failed: " + e.getMessage());
            }
            return;
        }

        if (state == Watcher.Event.KeeperState.Disconnected) {
            connectionState = "DISCONNECTED";
            publishState();
            return;
        }

        if (state == Watcher.Event.KeeperState.Expired) {
            connectionState = "SESSION_EXPIRED";
            publishState();
            return;
        }

        try {
            if (type == Watcher.Event.EventType.NodeDeleted && rootPath.equals(path)) {
                handleNodeDeleted();
                zk.exists(rootPath, this);
                publishState();
                return;
            }

            if ((type == Watcher.Event.EventType.NodeCreated || type == Watcher.Event.EventType.NodeDataChanged)
                    && rootPath.equals(path)) {
                handleNodePresent();
                publishState();
                return;
            }

            if (nodeAExists && isSubtreeChange(type)
                    && (path == null || isWithinSubtree(path))) {
                refreshDescendantsAndTree();
                publishState();
            }
        } catch (Exception e) {
            log.error("Error handling watch event", e);
            broadcaster.broadcastLog("Watch handler error: " + e.getMessage());
        }
    }

    private boolean isSubtreeChange(Watcher.Event.EventType type) {
        return type == Watcher.Event.EventType.NodeCreated
                || type == Watcher.Event.EventType.NodeChildrenChanged
                || type == Watcher.Event.EventType.NodeDeleted
                || type == Watcher.Event.EventType.NodeDataChanged;
    }

    private boolean isWithinSubtree(String path) {
        return path.equals(rootPath) || path.startsWith(rootPath + "/");
    }

    private void syncState() throws KeeperException, InterruptedException {
        Stat stat = zk.exists(rootPath, this);
        if (stat != null) {
            handleNodePresent();
        } else {
            handleNodeAbsent();
            zk.exists(rootPath, this);
        }
        publishState();
    }

    private void handleNodePresent() throws KeeperException, InterruptedException {
        nodeAExists = true;
        try {
            externalAppLauncher.start();
            broadcaster.broadcastLog("External application launched (znode " + rootPath + " exists)");
        } catch (Exception e) {
            log.error("Failed to start external application", e);
            broadcaster.broadcastLog("Failed to start external app: " + e.getMessage());
        }
        registerSubtreeWatch();
        refreshDescendantsAndTree();
        zk.exists(rootPath, this);
    }

    private void registerSubtreeWatch() throws KeeperException, InterruptedException {
        zk.addWatch(rootPath, this, AddWatchMode.PERSISTENT_RECURSIVE);
    }

    private void handleNodeAbsent() {
        nodeAExists = false;
        childCount = 0;
        lastKnownDescendantCount = -1;
        tree = null;
        try {
            externalAppLauncher.stop();
            broadcaster.broadcastLog("External application stopped (znode " + rootPath + " absent)");
        } catch (Exception e) {
            log.error("Failed to stop external application", e);
            broadcaster.broadcastLog("Failed to stop external app: " + e.getMessage());
        }
    }

    private void handleNodeDeleted() throws KeeperException, InterruptedException {
        handleNodeAbsent();
    }

    private void refreshDescendantsAndTree() throws KeeperException, InterruptedException {
        int newCount = treeBuilder.countDescendants(zk, rootPath);
        if (lastKnownDescendantCount >= 0 && newCount != lastKnownDescendantCount) {
            String message = newCount > lastKnownDescendantCount
                    ? "Potomek dodany — liczba potomków: " + newCount
                    : "Potomek usunięty — liczba potomków: " + newCount;
            broadcaster.broadcastNotification(message, newCount);
            log.info(message);
        }
        lastKnownDescendantCount = newCount;
        childCount = newCount;
        tree = treeBuilder.buildTree(zk, rootPath);
        registerChildrenWatchesRecursive(rootPath);
    }

    private void registerChildrenWatchesRecursive(String path) throws KeeperException, InterruptedException {
        List<String> children = zk.getChildren(path, this);
        for (String child : children) {
            registerChildrenWatchesRecursive(childPath(path, child));
        }
    }

    private String childPath(String parentPath, String childName) {
        return parentPath.endsWith("/") ? parentPath + childName : parentPath + "/" + childName;
    }

    public AppState getAppState() {
        return new AppState(
                connectionState,
                nodeAExists,
                childCount,
                externalAppLauncher != null && externalAppLauncher.isRunning(),
                tree
        );
    }

    private void publishState() {
        broadcaster.broadcastState(getAppState());
    }
}
