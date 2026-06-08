package pl.distributed.zkwatcher.model;

import java.util.ArrayList;
import java.util.List;

public class TreeNode {

    private final String name;
    private final String path;
    private final String data;
    private final List<TreeNode> children = new ArrayList<>();

    public TreeNode(String name, String path, String data) {
        this.name = name;
        this.path = path;
        this.data = data;
    }

    public String getName() {
        return name;
    }

    public String getPath() {
        return path;
    }

    public String getData() {
        return data;
    }

    public List<TreeNode> getChildren() {
        return children;
    }

    public void addChild(TreeNode child) {
        children.add(child);
    }
}
