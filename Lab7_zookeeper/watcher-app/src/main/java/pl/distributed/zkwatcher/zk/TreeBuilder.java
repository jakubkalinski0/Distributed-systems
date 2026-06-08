package pl.distributed.zkwatcher.zk;

import org.apache.zookeeper.KeeperException;
import org.apache.zookeeper.ZooKeeper;
import org.apache.zookeeper.data.Stat;
import pl.distributed.zkwatcher.model.TreeNode;

import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;

public class TreeBuilder {

    public TreeNode buildTree(ZooKeeper zk, String rootPath) throws KeeperException, InterruptedException {
        Stat stat = zk.exists(rootPath, false);
        if (stat == null) {
            return null;
        }
        String name = rootPath.equals("/") ? "/" : rootPath.substring(rootPath.lastIndexOf('/') + 1);
        byte[] dataBytes = zk.getData(rootPath, false, stat);
        String data = dataBytes == null ? "" : new String(dataBytes, StandardCharsets.UTF_8);
        TreeNode node = new TreeNode(name, rootPath, data);

        List<String> children = zk.getChildren(rootPath, false);
        Collections.sort(children);
        for (String child : children) {
            String childPath = rootPath.endsWith("/") ? rootPath + child : rootPath + "/" + child;
            node.addChild(buildTree(zk, childPath));
        }
        return node;
    }

    public int countDescendants(ZooKeeper zk, String rootPath) throws KeeperException, InterruptedException {
        int count = 0;
        List<String> children = zk.getChildren(rootPath, false);
        for (String child : children) {
            String childPath = childPath(rootPath, child);
            count += 1 + countDescendants(zk, childPath);
        }
        return count;
    }

    private String childPath(String parentPath, String childName) {
        return parentPath.endsWith("/") ? parentPath + childName : parentPath + "/" + childName;
    }
}
