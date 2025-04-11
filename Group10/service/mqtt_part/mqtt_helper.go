package mqtt_part

import (
	"fmt"
	"log"
	"service/config"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
)

var messagePubHandler mqtt.MessageHandler = func(client mqtt.Client, msg mqtt.Message) {
	log.Printf("Received message: %s from topic: %s\n", msg.Payload(), msg.Topic())
}

var connectHandler mqtt.OnConnectHandler = func(client mqtt.Client) {
	log.Println("Connected to MQTT broker")
}

var connectLostHandler mqtt.ConnectionLostHandler = func(client mqtt.Client, err error) {
	log.Printf("Connection lost: %v", err)
}

var client mqtt.Client = nil

func init() {
	opts := mqtt.NewClientOptions()
	port := config.DeployConfig.Hivemq.Port
	opts.AddBroker(fmt.Sprintf("tls://%s:%d", config.DeployConfig.Hivemq.URL, port))
	opts.SetClientID(config.DeployConfig.Hivemq.ClientId)
	opts.SetUsername(config.DeployConfig.Hivemq.Username)
	opts.SetPassword(config.DeployConfig.Hivemq.Password)
	opts.SetDefaultPublishHandler(messagePubHandler)
	opts.OnConnect = connectHandler
	opts.OnConnectionLost = connectLostHandler

	client = mqtt.NewClient(opts)
	if token := client.Connect(); token.Wait() && token.Error() != nil {
		panic(fmt.Sprintf("MQTT connection failed: %v", token.Error()))
	}
}

func Publish(topic string, rawMsg []byte, retry int) error {
	for i := 0; i < retry; i++ {
		token := client.Publish(topic, 1, false, rawMsg)
		if !token.WaitTimeout(5 * time.Second) {
			log.Printf("Publish timeout: %v", token.Error())
			continue
		}
		if token.Error() != nil {
			log.Printf("Publish error: %v", token.Error())
			continue
		}
		return token.Error()
	}
	return nil
}

func Cleanup() {
	if client != nil {
		client.Disconnect(250)
	}
	log.Println("Disconnected from MQTT broker")
}
