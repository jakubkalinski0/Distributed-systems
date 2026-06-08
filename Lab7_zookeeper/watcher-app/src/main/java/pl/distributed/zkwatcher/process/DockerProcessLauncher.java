package pl.distributed.zkwatcher.process;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

public class DockerProcessLauncher implements ExternalAppLauncher {

    private static final Logger log = LoggerFactory.getLogger(DockerProcessLauncher.class);

    private final String containerName;
    private volatile boolean running;

    public DockerProcessLauncher(String containerName) {
        this.containerName = containerName;
    }

    @Override
    public synchronized void start() throws Exception {
        if (isRunning()) {
            log.info("Docker container '{}' already running", containerName);
            return;
        }
        log.info("Starting Docker container '{}'", containerName);
        runDocker("start", containerName);
        running = true;
        log.info("Docker container '{}' started", containerName);
    }

    @Override
    public synchronized void stop() throws Exception {
        if (!isRunning()) {
            log.info("Docker container '{}' is not running", containerName);
            return;
        }
        log.info("Stopping Docker container '{}'", containerName);
        runDocker("stop", containerName);
        running = false;
        log.info("Docker container '{}' stopped", containerName);
    }

    @Override
    public synchronized boolean isRunning() {
        try {
            String status = runDockerCapture("inspect", "-f", "{{.State.Running}}", containerName).trim();
            running = "true".equalsIgnoreCase(status);
            return running;
        } catch (Exception e) {
            running = false;
            return false;
        }
    }

    private void runDocker(String... args) throws Exception {
        String output = runDockerCapture(args);
        if (!output.isBlank()) {
            log.debug("docker {}: {}", String.join(" ", args), output);
        }
    }

    private String runDockerCapture(String... args) throws Exception {
        String[] command = new String[args.length + 1];
        command[0] = "docker";
        System.arraycopy(args, 0, command, 1, args.length);

        ProcessBuilder builder = new ProcessBuilder(command);
        builder.redirectErrorStream(true);
        Process process = builder.start();

        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append('\n');
            }
        }

        if (!process.waitFor(30, TimeUnit.SECONDS)) {
            process.destroyForcibly();
            throw new IllegalStateException("docker command timed out: " + String.join(" ", command));
        }
        if (process.exitValue() != 0) {
            throw new IllegalStateException(
                    "docker command failed (" + process.exitValue() + "): "
                            + String.join(" ", command) + " -> " + output);
        }
        return output.toString();
    }
}
