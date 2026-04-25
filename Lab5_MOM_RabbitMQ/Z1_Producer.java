import com.rabbitmq.client.*;

import java.io.BufferedReader;
import java.io.InputStreamReader;

public class Z1_Producer {

    private final static String QUEUE_NAME = "lab_queue";

    public static void main(String[] argv) throws Exception {

        System.out.println("Z1 PRODUCER");

        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost("localhost");

        Connection connection = factory.newConnection();
        Channel channel = connection.createChannel();

        channel.queueDeclare(QUEUE_NAME, false, false, false, null);

        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));

        while (true) {
            System.out.print("Podaj czas (1 lub 5): ");
            String msg = br.readLine();

            channel.basicPublish("", QUEUE_NAME, null, msg.getBytes("UTF-8"));
            System.out.println("Wysłano: " + msg);
        }
    }
}