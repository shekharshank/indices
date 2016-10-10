// Reads  collectd data from amqp queue and logs data in influxdb database
// supports libvirt plugin 
// supports shekharshank/collectd-linux-perf
// supports shekharshank/collectd-with-docker
 
	
package main

import (
	"flag"
	"fmt"
	"github.com/streadway/amqp"
	"log"
	"time"
	"strings"
	"encoding/json"
	"github.com/influxdata/influxdb/client/v2"
)

const (
    MyDB = "collectd-db"
    //measurement = "system_metrics"
    username = "user"
    password = "pass"
)


var (
	uri          = flag.String("uri", "amqp://<user>:<pass>@0.0.0.0:5672", "AMQP URI")
	exchange     = flag.String("exchange", "collectd-exchange", "Durable, non-auto-deleted AMQP exchange name")
	exchangeType = flag.String("exchange-type", "direct", "Exchange type - direct|fanout|topic|x-custom")
	queue        = flag.String("queue", "<collectd-queue>", "Ephemeral AMQP queue name")
	bindingKey   = flag.String("key", "<collectd-key>", "AMQP binding key")
	consumerTag  = flag.String("consumer-tag", "simple-consumer", "AMQP consumer tag (should not be blank)")
	lifetime     = flag.Duration("lifetime", 0*time.Second, "lifetime of process before shutdown (0s=infinite)")
)

func init() {
	flag.Parse()
}

func main() {

	influxc, err := client.NewHTTPClient(client.HTTPConfig{
                Addr: "http://localhost:8086",
                Username: username,
                Password: password,
            })
        if err != nil {
                log.Fatalln("Error: ", err)
        }

	c, err := NewConsumer(*uri, *exchange, *exchangeType, *queue, *bindingKey, *consumerTag, influxc)
	if err != nil {
		log.Fatalf("%s", err)
	}

	if *lifetime > 0 {
		log.Printf("running for %s", *lifetime)
		time.Sleep(*lifetime)
	} else {
		log.Printf("running forever")
		select {}
	}

	log.Printf("shutting down")

	if err := c.Shutdown(); err != nil {
		log.Fatalf("error during shutdown: %s", err)
	}
}

type Consumer struct {
	conn    *amqp.Connection
	channel *amqp.Channel
	tag     string
	done    chan error
}

type PerfMetric struct {
        MetricTimestamp float64       `json:"time"`
        Host      string    `json:"host"`
        Plugin      string    `json:"plugin"`
        PluginInstance      string    `json:"plugin_instance"`
        Type      string    `json:"type"`
        TypeInstance      string    `json:"type_instance"`
        TimeInterval float32        `json:"interval"`
        Parameters[]     string    `json:"dsnames"`
        Values[] float64 `json:"values"`
}


func NewConsumer(amqpURI, exchange, exchangeType, queueName, key, ctag string, dbClient client.Client) (*Consumer, error) {
	c := &Consumer{
		conn:    nil,
		channel: nil,
		tag:     ctag,
		done:    make(chan error),
	}

	var err error

	log.Printf("dialing %q", amqpURI)
	c.conn, err = amqp.Dial(amqpURI)
	if err != nil {
		return nil, fmt.Errorf("Dial: %s", err)
	}

	go func() {
		fmt.Printf("closing: %s", <-c.conn.NotifyClose(make(chan *amqp.Error)))
	}()

	log.Printf("got Connection, getting Channel")
	c.channel, err = c.conn.Channel()
	if err != nil {
		return nil, fmt.Errorf("Channel: %s", err)
	}

	log.Printf("got Channel, declaring Exchange (%q)", exchange)
	if err = c.channel.ExchangeDeclare(
		exchange,     // name of the exchange
		exchangeType, // type
		true,         // durable
		false,        // delete when complete
		false,        // internal
		false,        // noWait
		nil,          // arguments
	); err != nil {
		return nil, fmt.Errorf("Exchange Declare: %s", err)
	}

	log.Printf("declared Exchange, declaring Queue %q", queueName)
	queue, err := c.channel.QueueDeclare(
		queueName, // name of the queue
		true,      // durable
		false,     // delete when usused
		false,     // exclusive
		false,     // noWait
		nil,       // arguments
	)
	if err != nil {
		return nil, fmt.Errorf("Queue Declare: %s", err)
	}

	log.Printf("declared Queue (%q %d messages, %d consumers), binding to Exchange (key %q)",
		queue.Name, queue.Messages, queue.Consumers, key)

	if err = c.channel.QueueBind(
		queue.Name, // name of the queue
		key,        // bindingKey
		exchange,   // sourceExchange
		false,      // noWait
		nil,        // arguments
	); err != nil {
		return nil, fmt.Errorf("Queue Bind: %s", err)
	}

	log.Printf("Queue bound to Exchange, starting Consume (consumer tag %q)", c.tag)
	deliveries, err := c.channel.Consume(
		queue.Name, // name
		c.tag,      // consumerTag,
		false,      // noAck
		false,      // exclusive
		false,      // noLocal
		false,      // noWait
		nil,        // arguments
	)
	if err != nil {
		return nil, fmt.Errorf("Queue Consume: %s", err)
	}

	go handle(dbClient, deliveries, c.done)

	return c, nil
}

func (c *Consumer) Shutdown() error {
	// will close() the deliveries channel
	if err := c.channel.Cancel(c.tag, true); err != nil {
		return fmt.Errorf("Consumer cancel failed: %s", err)
	}

	if err := c.conn.Close(); err != nil {
		return fmt.Errorf("AMQP connection close error: %s", err)
	}

	defer log.Printf("AMQP shutdown OK")

	// wait for handle() to exit
	return <-c.done
}

func handle(dbClient client.Client, deliveries <-chan amqp.Delivery, done chan error) {

	log.Printf("Recieving ...")

	for d := range deliveries {

		var m[] PerfMetric
		s := string(d.Body)
		//log.Println(s)
		jsonerr := json.NewDecoder(strings.NewReader(s)).Decode(&m)
		if jsonerr != nil {
		    log.Println(jsonerr.Error())
		    return
		}
	//	 log.Println(m)
		writePoints(dbClient, m[0])
		d.Ack(false)
	}
	log.Printf("handle: deliveries channel closed")
	done <- nil
}

func writePoints(clnt client.Client, m PerfMetric) {
	measurement := "host_metrics"

	// Create a new point batch
	    bp, err := client.NewBatchPoints(client.BatchPointsConfig{
		Database:  MyDB,
		Precision: "s",
	    })

	    if err != nil {
		log.Fatalln("Error: ", err)
	    }

	    // Create a point and add to batch
	   fields := make(map[string]interface{})

	   tags := map[string]string{
		    "host":   m.Host,
	   }

	   fields["interval"] = m.TimeInterval

	   switch m.Plugin {

		case "virt" :
			measurement = "vm_metrics"
			tags["instance"] = m.PluginInstance

			if m.Type  ==  "memory" {
				fields[m.Type + "_" + m.TypeInstance] = m.Values[0]
			} else if  m.Type == "virt_cpu_total"{
				fields[m.Type] = m.Values[0]
			} else if m.Type == "virt_vcpu" {
				return
			} else {
				for i := range m.Parameters {
					fields[m.Type + "_" +  m.Parameters[i]] = m.Values[i]
				}
			}
			break

		case "docker" :
                        measurement = "container_metrics"
                        tags["instance"] = m.PluginInstance
			
			if len(m.Parameters)  == 1 {
				fields[m.Type] = m.Values[0]
                        } else {
                                for i := range m.Parameters  {
                                        fields[m.Type + "_" +  m.Parameters[i]] = m.Values[i]
                                }
                        }

                        break


		case "linux_perf":

		        if m.PluginInstance == "all" {
				measurement = "host_metrics_micro"
                        } else {
				measurement = "vm_metrics_micro"
                                tags["instance"] = m.PluginInstance
                        }
			any_value := false			
			for i := range m.Parameters  {
				if (m.Values[i] != -1.0) {
					fields[m.Parameters[i]] = m.Values[i]
					any_value = true
				}
			}
			if (!any_value){
				return
			}
                        break

			
		case "aggregation":
			measurement = "vm_metrics"
			if strings.HasSuffix(m.PluginInstance,"-num") {
				tags["instance"] = m.PluginInstance[:len(m.PluginInstance)-4]
				fields["vcpu_count"] = 	int(m.Values[0] + 0.5)
			} else if strings.HasSuffix(m.PluginInstance,"-average") {
				tags["instance"] = m.PluginInstance[:len(m.PluginInstance)-8]
				fields["vcpu_avg"] = m.Values[0] 
			} else	{
				tags["instance"] = m.PluginInstance[:len(m.PluginInstance)-4]
				fields["vcpu_sum"] = m.Values[0] 
			}
			break
		default:
			measurement = "host_metrics"
			// parse according to needed fields

			if len(m.Parameters)  == 1 {
				if m.Type == "percent" {
					fields["cpu"] = m.Values[0]
				} else {
					fields[m.Type] = m.Values[0]
				}
			} else {
				for i := range m.Parameters  {
					fields[m.Type + "_" +  m.Parameters[i]] = m.Values[i]
				}
			}
		
	   }

	performanceTime := time.Unix(int64(m.MetricTimestamp + 0.5 ), 0)
//		log.Printf(performanceTime.String())
	
    pt, err := client.NewPoint(measurement, tags, fields, performanceTime)

    if err != nil {
        log.Fatalln("Error: ", err)
    }

    bp.AddPoint(pt)

    // Write the batch
    err = clnt.Write(bp)

   if err != nil {
	log.Fatalf("unexpected error.  %v", err)
   }
}
