package pl.distributed.zkwatcher.process;

public interface ExternalAppLauncher {

    void start() throws Exception;

    void stop() throws Exception;

    boolean isRunning();
}
