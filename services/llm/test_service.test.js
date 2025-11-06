const request = require('supertest');
const { describe, it, before, after } = require('mocha');
const { expect } = require('chai');

// We'll test the actual running service
const BASE_URL = 'http://localhost:8004';

describe('LLM Service Tests', () => {
    describe('Health Endpoint', () => {
        it('should return status ok', async () => {
            const response = await request(BASE_URL)
                .get('/health')
                .expect(200);
            
            expect(response.body).to.have.property('status', 'ok');
            expect(response.body).to.have.property('service', 'llm');
        });
    });

    describe('Answer Endpoint', () => {
        it('should answer a simple banking question', async () => {
            const response = await request(BASE_URL)
                .post('/answer')
                .send({ question: 'What is a savings account?' })
                .expect(200);
            
            expect(response.body).to.have.property('answer');
            expect(response.body.answer).to.be.a('string');
            expect(response.body.answer.length).to.be.greaterThan(10);
            expect(response.body).to.have.property('confidence');
            expect(response.body.confidence).to.be.a('number');
            expect(response.body.confidence).to.be.within(0, 1);
        });

        it('should handle questions with context', async () => {
            const response = await request(BASE_URL)
                .post('/answer')
                .send({
                    question: 'What is my balance?',
                    context: { account_id: 'alice', balance: 1500 }
                })
                .expect(200);
            
            expect(response.body).to.have.property('answer');
            expect(response.body.answer).to.be.a('string');
        });

        it('should return error for empty question', async () => {
            const response = await request(BASE_URL)
                .post('/answer')
                .send({ question: '' })
                .expect(400);
            
            expect(response.body).to.have.property('error');
        });

        it('should handle banking-specific questions', async () => {
            const bankingQuestions = [
                'How do I transfer money?',
                'What are the interest rates?',
                'How do I check my balance?',
                'What is a checking account?',
            ];

            for (const question of bankingQuestions) {
                const response = await request(BASE_URL)
                    .post('/answer')
                    .send({ question })
                    .expect(200);
                
                expect(response.body.answer).to.be.a('string');
                expect(response.body.answer.length).to.be.greaterThan(10);
            }
        }).timeout(30000); // Increase timeout for multiple API calls

        it('should answer questions about fraud', async () => {
            const response = await request(BASE_URL)
                .post('/answer')
                .send({ question: 'How does fraud detection work?' })
                .expect(200);
            
            expect(response.body.answer).to.be.a('string');
            expect(response.body.answer.toLowerCase()).to.match(/fraud|security|protect|detect/);
        });

        it('should handle complex banking scenarios', async () => {
            const response = await request(BASE_URL)
                .post('/answer')
                .send({
                    question: 'I want to transfer $500 but I got a fraud alert. What should I do?',
                    context: { 
                        recent_fraud_alert: true,
                        balance: 1000 
                    }
                })
                .expect(200);
            
            expect(response.body.answer).to.be.a('string');
            expect(response.body.confidence).to.be.within(0, 1);
        });
    });

    describe('Logs Endpoint', () => {
        it('should return logs array', async () => {
            const response = await request(BASE_URL)
                .get('/logs')
                .expect(200);
            
            expect(response.body).to.be.an('array');
        });

        it('should respect limit parameter', async () => {
            const response = await request(BASE_URL)
                .get('/logs?limit=5')
                .expect(200);
            
            expect(response.body).to.be.an('array');
            expect(response.body.length).to.be.at.most(5);
        });

        it('should return logs with correct structure', async () => {
            // First, make a request to generate a log
            await request(BASE_URL)
                .post('/answer')
                .send({ question: 'Test question' });

            const response = await request(BASE_URL)
                .get('/logs?limit=1')
                .expect(200);
            
            if (response.body.length > 0) {
                const log = response.body[0];
                expect(log).to.have.property('timestamp');
                expect(log).to.have.property('level');
                expect(log).to.have.property('service', 'llm');
                expect(log).to.have.property('message');
            }
        });
    });

    describe('Metrics Endpoint', () => {
        it('should return metrics object', async () => {
            const response = await request(BASE_URL)
                .get('/metrics')
                .expect(200);
            
            expect(response.body).to.be.an('object');
            expect(response.body).to.have.property('service', 'llm');
            expect(response.body).to.have.property('timestamp');
            expect(response.body).to.have.property('counters');
            expect(response.body).to.have.property('gauges');
            expect(response.body).to.have.property('time_series');
        });

        it('should track question counters', async () => {
            // Make a few requests
            await request(BASE_URL)
                .post('/answer')
                .send({ question: 'Test 1' });
            
            await request(BASE_URL)
                .post('/answer')
                .send({ question: 'Test 2' });

            const response = await request(BASE_URL)
                .get('/metrics')
                .expect(200);
            
            expect(response.body.counters).to.have.property('questions_total');
            expect(response.body.counters.questions_total).to.be.a('number');
            expect(response.body.counters.questions_total).to.be.at.least(2);
        });

        it('should respect period parameter', async () => {
            const response = await request(BASE_URL)
                .get('/metrics?period=5')
                .expect(200);
            
            expect(response.body).to.have.property('time_series');
        });

        it('should track answer duration timing', async () => {
            // Make a request to generate timing data
            await request(BASE_URL)
                .post('/answer')
                .send({ question: 'What is a loan?' });

            const response = await request(BASE_URL)
                .get('/metrics')
                .expect(200);
            
            expect(response.body.time_series).to.have.property('answer_duration');
            expect(response.body.time_series.answer_duration).to.be.an('array');
        });
    });

    describe('Error Handling', () => {
        it('should handle missing request body', async () => {
            const response = await request(BASE_URL)
                .post('/answer')
                .send({})
                .expect(400);
            
            expect(response.body).to.have.property('error');
        });
    });

    describe('Performance Tests', () => {
        it('should respond to health check quickly', async () => {
            const start = Date.now();
            await request(BASE_URL)
                .get('/health')
                .expect(200);
            const duration = Date.now() - start;
            
            expect(duration).to.be.lessThan(500);
        });

        it('should handle multiple concurrent requests', async () => {
            const promises = [];
            for (let i = 0; i < 3; i++) {
                promises.push(
                    request(BASE_URL)
                        .post('/answer')
                        .send({ question: `Concurrent question ${i}` })
                );
            }

            const responses = await Promise.all(promises);
            
            responses.forEach(response => {
                expect(response.status).to.equal(200);
                expect(response.body).to.have.property('answer');
            });
        }).timeout(30000);
    });

    describe('Integration Tests', () => {
        it('should maintain service state across requests', async () => {
            // Get initial metrics
            const metrics1 = await request(BASE_URL)
                .get('/metrics')
                .expect(200);
            
            const initialCount = metrics1.body.counters.questions_total || 0;

            // Make a request
            await request(BASE_URL)
                .post('/answer')
                .send({ question: 'State test question' })
                .expect(200);

            // Check metrics increased
            const metrics2 = await request(BASE_URL)
                .get('/metrics')
                .expect(200);
            
            expect(metrics2.body.counters.questions_total).to.be.greaterThan(initialCount);
        });

        it('should log all requests properly', async () => {
            const uniqueQuestion = `Test question at ${Date.now()}`;
            
            await request(BASE_URL)
                .post('/answer')
                .send({ question: uniqueQuestion })
                .expect(200);

            const logs = await request(BASE_URL)
                .get('/logs?limit=50')
                .expect(200);
            
            const relevantLog = logs.body.find(log => 
                log.message && log.message.includes(uniqueQuestion.substring(0, 20))
            );
            
            expect(relevantLog).to.exist;
        });
    });

    describe('Response Quality Tests', () => {
        it('should provide relevant answers for banking questions', async () => {
            const testCases = [
                {
                    question: 'What is a credit card?',
                    expectedKeywords: ['card', 'credit', 'payment', 'purchase', 'money']
                },
                {
                    question: 'How do I deposit money?',
                    expectedKeywords: ['deposit', 'account', 'money', 'bank', 'cash']
                }
            ];

            for (const testCase of testCases) {
                const response = await request(BASE_URL)
                    .post('/answer')
                    .send({ question: testCase.question })
                    .expect(200);
                
                const answer = response.body.answer.toLowerCase();
                const hasRelevantKeyword = testCase.expectedKeywords.some(
                    keyword => answer.includes(keyword)
                );
                
                expect(hasRelevantKeyword).to.be.true;
                expect(answer.length).to.be.greaterThan(20);
            }
        }).timeout(30000);

        it('should provide coherent multi-sentence answers', async () => {
            const response = await request(BASE_URL)
                .post('/answer')
                .send({ question: 'Can you explain how checking accounts work?' })
                .expect(200);
            
            expect(response.body.answer).to.be.a('string');
            expect(response.body.answer.length).to.be.greaterThan(30);
        });
    });
});
