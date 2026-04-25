import com.rabbitmq.client.*;

public class Z1_Consumer {

    private final static String QUEUE_NAME = "lab_queue";

    public static void main(String[] argv) throws Exception {

        System.out.println("Z1 CONSUMER");

        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost("localhost");

        Connection connection = factory.newConnection();
        Channel channel = connection.createChannel();

        channel.queueDeclare(QUEUE_NAME, false, false, false, null);

        channel.basicQos(1);

        DeliverCallback deliverCallback = (consumerTag, delivery) -> {

            String message = new String(delivery.getBody(), "UTF-8");
            System.out.println("Odebrano: " + message);

            try {
                int timeToSleep = Integer.parseInt(message);
                Thread.sleep(timeToSleep * 1000);

                System.out.println("Zakończono: " + message);

                channel.basicAck(delivery.getEnvelope().getDeliveryTag(), false);

            } catch (Exception e) {
                e.printStackTrace();
            }
        };

        channel.basicConsume(QUEUE_NAME, false, deliverCallback, consumerTag -> {});
    }
}