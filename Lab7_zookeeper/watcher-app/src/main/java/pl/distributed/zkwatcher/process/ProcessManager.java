package pl.distributed.zkwatcher.process;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

public class ProcessManager implements ExternalAppLauncher {

    private static final Logger log = LoggerFactory.getLogger(ProcessManager.class);

    private final List<String> command;
    private Process process;

    public ProcessManager(List<String> command) {
        this.command = command;
    }

    @Override
    public synchronized void start() throws Exception {
        if (isRunning()) {
            log.info("External process already running (pid={})", process.pid());
            return;
        }
        log.info("Starting external process: {}", String.join(" ", command));
        ProcessBuilder builder = new ProcessBuilder(command);
        builder.redirectErrorStream(true);
        process = builder.start();
        log.info("External process started (pid={})", process.pid());
    }

    @Override
    public synchronized void stop() throws Exception {
        if (!isRunning()) {
            log.info("External process is not running");
            return;
        }
        log.info("Stopping external process (pid={})", process.pid());
        process.destroy();
        if (!process.waitFor(5, java.util.concurrent.TimeUnit.SECONDS)) {
            process.destroyForcibly();
        }
        process = null;
        log.info("External process stopped");
    }

    @Override
    public synchronized boolean isRunning() {
        return process != null && process.isAlive();
    }
}
