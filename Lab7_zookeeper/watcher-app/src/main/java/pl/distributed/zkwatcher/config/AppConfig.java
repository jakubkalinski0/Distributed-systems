package pl.distributed.zkwatcher.config;

import java.util.Arrays;
import java.util.List;

public final class AppConfig {

    private final String zkConnectString;
    private final String zkRootPath;
    private final int sessionTimeoutMs;
    private final int httpPort;
    private final ExternalAppMode externalAppMode;
    private final List<String> externalAppCommand;
    private final String externalDockerContainer;

    private AppConfig(
            String zkConnectString,
            String zkRootPath,
            int sessionTimeoutMs,
            int httpPort,
            ExternalAppMode externalAppMode,
            List<String> externalAppCommand,
            String externalDockerContainer) {
        this.zkConnectString = zkConnectString;
        this.zkRootPath = zkRootPath;
        this.sessionTimeoutMs = sessionTimeoutMs;
        this.httpPort = httpPort;
        this.externalAppMode = externalAppMode;
        this.externalAppCommand = List.copyOf(externalAppCommand);
        this.externalDockerContainer = externalDockerContainer;
    }

    public static AppConfig fromArgs(String[] args) {
        String zkConnect = envOrDefault("ZK_CONNECT_STRING", "localhost:2181");
        String zkRootPath = envOrDefault("ZK_ROOT_PATH", "/a");
        int sessionTimeout = Integer.parseInt(envOrDefault("ZK_SESSION_TIMEOUT_MS", "30000"));
        int httpPort = Integer.parseInt(envOrDefault("HTTP_PORT", "8080"));
        ExternalAppMode mode = ExternalAppMode.from(envOrDefault("EXTERNAL_APP_MODE", "process"));
        String dockerContainer = envOrDefault("EXTERNAL_DOCKER_CONTAINER", "external-gui");
        List<String> externalCommand = defaultExternalCommand();

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--zk-connect" -> zkConnect = requireValue(args, ++i, "--zk-connect");
                case "--zk-root" -> zkRootPath = requireValue(args, ++i, "--zk-root");
                case "--session-timeout" -> sessionTimeout = Integer.parseInt(requireValue(args, ++i, "--session-timeout"));
                case "--http-port" -> httpPort = Integer.parseInt(requireValue(args, ++i, "--http-port"));
                case "--external-app-mode" -> mode = ExternalAppMode.from(requireValue(args, ++i, "--external-app-mode"));
                case "--external-docker-container" -> dockerContainer = requireValue(args, ++i, "--external-docker-container");
                case "--external-app" -> externalCommand = parseCommand(requireValue(args, ++i, "--external-app"));
                default -> throw new IllegalArgumentException("Unknown argument: " + args[i]);
            }
        }

        if (!zkRootPath.startsWith("/")) {
            zkRootPath = "/" + zkRootPath;
        }

        return new AppConfig(zkConnect, zkRootPath, sessionTimeout, httpPort, mode, externalCommand, dockerContainer);
    }

    private static List<String> defaultExternalCommand() {
        String os = System.getProperty("os.name", "").toLowerCase();
        if (os.contains("win")) {
            return List.of("calc.exe");
        }
        if (os.contains("mac")) {
            return List.of("open", "-a", "Calculator");
        }
        return List.of("xdg-open", "https://example.com");
    }

    private static List<String> parseCommand(String commandLine) {
        if (commandLine == null || commandLine.isBlank()) {
            return defaultExternalCommand();
        }
        return Arrays.asList(commandLine.trim().split("\\s+"));
    }

    private static String envOrDefault(String key, String defaultValue) {
        String value = System.getenv(key);
        return value != null && !value.isBlank() ? value : defaultValue;
    }

    private static String requireValue(String[] args, int index, String flag) {
        if (index >= args.length) {
            throw new IllegalArgumentException("Missing value for " + flag);
        }
        return args[index];
    }

    public String getZkConnectString() {
        return zkConnectString;
    }

    public String getZkRootPath() {
        return zkRootPath;
    }

    public int getSessionTimeoutMs() {
        return sessionTimeoutMs;
    }

    public int getHttpPort() {
        return httpPort;
    }

    public ExternalAppMode getExternalAppMode() {
        return externalAppMode;
    }

    public List<String> getExternalAppCommand() {
        return externalAppCommand;
    }

    public String getExternalDockerContainer() {
        return externalDockerContainer;
    }

    public enum ExternalAppMode {
        PROCESS,
        DOCKER;

        public static ExternalAppMode from(String value) {
            return switch (value.toLowerCase()) {
                case "process", "host" -> PROCESS;
                case "docker" -> DOCKER;
                default -> throw new IllegalArgumentException("Unknown external app mode: " + value);
            };
        }
    }
}
