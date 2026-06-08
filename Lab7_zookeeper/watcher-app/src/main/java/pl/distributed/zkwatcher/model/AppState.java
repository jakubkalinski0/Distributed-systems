package pl.distributed.zkwatcher.model;

public class AppState {

    private final String zkConnectionState;
    private final boolean nodeAExists;
    private final int childCount;
    private final boolean externalAppRunning;
    private final TreeNode tree;

    public AppState(
            String zkConnectionState,
            boolean nodeAExists,
            int childCount,
            boolean externalAppRunning,
            TreeNode tree) {
        this.zkConnectionState = zkConnectionState;
        this.nodeAExists = nodeAExists;
        this.childCount = childCount;
        this.externalAppRunning = externalAppRunning;
        this.tree = tree;
    }

    public String getZkConnectionState() {
        return zkConnectionState;
    }

    public boolean isNodeAExists() {
        return nodeAExists;
    }

    public int getChildCount() {
        return childCount;
    }

    public boolean isExternalAppRunning() {
        return externalAppRunning;
    }

    public TreeNode getTree() {
        return tree;
    }
}
