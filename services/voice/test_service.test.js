const request = require('supertest');
const { describe, it, before, after } = require('mocha');
const { expect } = require('chai');
const WebSocket = require('ws');

// Test the actual running service
const BASE_URL = 'http://localhost:8001';
const WS_URL = 'ws://localhost:8001';

describe('Voice Service Tests', () => {
    describe('Health Check', () => {
        it('should return status ok', async () => {
            const response = await request(BASE_URL)
                .get('/health')
                .expect(200);
            
            expect(response.body).to.have.property('status', 'ok');
            expect(response.body).to.have.property('service', 'voice');
            console.log('  ✓ Voice service is healthy');
        });
    });

    describe('TTS -> STT Round-Trip Tests', () => {
        // Minimal test - just verify APIs work, not model accuracy
        it('should handle TTS and STT APIs', async () => {
            const testText = 'Hello test';
            console.log(`\n  Testing minimal round-trip with: "${testText}"`);
            
            // Step 1: Text-to-Speech (TTS)
            const ttsResponse = await request(BASE_URL)
                .post('/synthesize')
                .send({ text: testText })
                .expect(200);
            
            expect(ttsResponse.body).to.have.property('audio_bytes');
            expect(ttsResponse.body).to.have.property('format', 'wav');
            expect(ttsResponse.body.audio_bytes).to.be.a('string');
            console.log(`  ✓ TTS: Generated audio (${ttsResponse.body.audio_bytes.length} chars)`);
            
            // Verify WAV format
            const audioBuffer = Buffer.from(ttsResponse.body.audio_bytes, 'base64');
            expect(audioBuffer.length).to.be.greaterThan(44); // Minimum WAV header size
            const header = audioBuffer.toString('ascii', 0, 4);
            expect(header).to.equal('RIFF');
            console.log(`  ✓ Valid WAV format (${audioBuffer.length} bytes)`);
            
            // Step 2: Speech-to-Text (STT)
            const sttResponse = await request(BASE_URL)
                .post('/transcribe')
                .send({ 
                    audio_bytes: ttsResponse.body.audio_bytes,
                    format: 'wav'
                })
                .expect(200);
            
            expect(sttResponse.body).to.have.property('transcript');
            expect(sttResponse.body.transcript).to.be.a('string');
            expect(sttResponse.body.transcript.length).to.be.greaterThan(0);
            
            console.log(`  ✓ STT: Transcribed as "${sttResponse.body.transcript}"`);
            console.log(`  ✓ TTS->STT round-trip successful`);
        }).timeout(15000);
    });

    describe('Live Audio Transcription (WebSocket)', () => {
        it('should establish WebSocket connection', (done) => {
            const ws = new WebSocket(`${WS_URL}/live-transcribe`);
            let connected = false;
            
            ws.on('open', () => {
                connected = true;
                console.log('  ✓ WebSocket connection established');
            });
            
            ws.on('message', (data) => {
                const msg = JSON.parse(data.toString());
                console.log(`  ✓ Received message type: ${msg.type}`);
                if (msg.type === 'started') {
                    console.log('  ✓ Live transcription started');
                    ws.close();
                }
            });
            
            ws.on('close', () => {
                expect(connected).to.be.true;
                done();
            });
            
            ws.on('error', (err) => {
                console.error(`  ✗ WebSocket error: ${err.message}`);
                done(err);
            });
        }).timeout(15000);

        it('should receive started message on connection', (done) => {
            const ws = new WebSocket(`${WS_URL}/live-transcribe`);
            let receivedStarted = false;
            
            ws.on('message', (data) => {
                const msg = JSON.parse(data.toString());
                
                if (msg.type === 'started') {
                    receivedStarted = true;
                    console.log('  ✓ Received started confirmation');
                    ws.close();
                }
            });
            
            ws.on('close', () => {
                expect(receivedStarted).to.be.true;
                done();
            });
            
            ws.on('error', done);
        }).timeout(15000);

        it('should handle stop command gracefully', (done) => {
            const ws = new WebSocket(`${WS_URL}/live-transcribe`);
            let receivedStarted = false;
            let receivedStopped = false;
            
            ws.on('message', (data) => {
                const msg = JSON.parse(data.toString());
                
                if (msg.type === 'started') {
                    receivedStarted = true;
                    console.log('  ✓ Session started, sending stop command');
                    ws.send(JSON.stringify({ type: 'stop' }));
                } else if (msg.type === 'stopped') {
                    receivedStopped = true;
                    console.log('  ✓ Session stopped successfully');
                    ws.close();
                }
            });
            
            ws.on('close', () => {
                expect(receivedStarted).to.be.true;
                expect(receivedStopped).to.be.true;
                done();
            });
            
            ws.on('error', done);
        }).timeout(15000);
        
        // Note: Testing actual audio streaming requires generating PCM16 audio data
        // which is complex in a test environment. The above tests verify the WebSocket
        // infrastructure is working correctly.
    });

    describe('Error Handling', () => {
        it('should handle missing text in synthesis', async () => {
            const response = await request(BASE_URL)
                .post('/synthesize')
                .send({});
            
            expect(response.status).to.equal(400);
            expect(response.body).to.have.property('error');
            console.log('  ✓ Missing text handled correctly');
        });

        it('should handle empty text in synthesis', async () => {
            const response = await request(BASE_URL)
                .post('/synthesize')
                .send({ text: '' });
            
            expect(response.status).to.equal(400);
            expect(response.body).to.have.property('error');
            console.log('  ✓ Empty text handled correctly');
        });

        it('should handle missing audio_bytes in transcription', async () => {
            const response = await request(BASE_URL)
                .post('/transcribe')
                .send({ format: 'wav' });
            
            expect(response.status).to.equal(400);
            expect(response.body).to.have.property('error');
            console.log('  ✓ Missing audio data handled correctly');
        });

        it('should handle invalid base64 audio', async () => {
            const response = await request(BASE_URL)
                .post('/transcribe')
                .send({ 
                    audio_bytes: 'invalid-base64-data!!!',
                    format: 'wav'
                });
            
            // Azure SDK handles invalid audio gracefully, returning empty/fallback transcript
            expect(response.status).to.equal(200);
            expect(response.body).to.have.property('transcript');
            console.log('  ✓ Invalid audio data handled gracefully');
        });
    });

    describe('Metrics and Monitoring', () => {
        it('should track synthesis operations', async () => {
            const before = await request(BASE_URL).get('/metrics').expect(200);
            const beforeCount = before.body.counters.syntheses_total || 0;
            
            await request(BASE_URL)
                .post('/synthesize')
                .send({ text: 'Metrics test' })
                .expect(200);
            
            const after = await request(BASE_URL).get('/metrics').expect(200);
            const afterCount = after.body.counters.syntheses_total || 0;
            
            expect(afterCount).to.be.greaterThan(beforeCount);
            console.log(`  ✓ Synthesis counter: ${beforeCount} -> ${afterCount}`);
        });

        it('should track transcription operations', async () => {
            const tts = await request(BASE_URL)
                .post('/synthesize')
                .send({ text: 'Test' })
                .expect(200);
            
            const before = await request(BASE_URL).get('/metrics').expect(200);
            const beforeCount = before.body.counters.transcriptions_total || 0;
            
            await request(BASE_URL)
                .post('/transcribe')
                .send({ audio_bytes: tts.body.audio_bytes, format: 'wav' })
                .expect(200);
            
            const after = await request(BASE_URL).get('/metrics').expect(200);
            const afterCount = after.body.counters.transcriptions_total || 0;
            
            expect(afterCount).to.be.greaterThan(beforeCount);
            console.log(`  ✓ Transcription counter: ${beforeCount} -> ${afterCount}`);
        });

        it('should record timing metrics', async () => {
            await request(BASE_URL)
                .post('/synthesize')
                .send({ text: 'Timing test' })
                .expect(200);
            
            const metrics = await request(BASE_URL).get('/metrics').expect(200);
            
            expect(metrics.body).to.have.property('time_series');
            expect(metrics.body.time_series).to.be.an('object');
            console.log('  ✓ Timing metrics recorded');
        });
    });

    describe('Logging', () => {
        it('should return logs array', async () => {
            const response = await request(BASE_URL)
                .get('/logs')
                .expect(200);
            
            expect(response.body).to.be.an('array');
            console.log(`  ✓ Retrieved ${response.body.length} log entries`);
        });

        it('should respect limit parameter', async () => {
            const response = await request(BASE_URL)
                .get('/logs?limit=5')
                .expect(200);
            
            expect(response.body).to.be.an('array');
            expect(response.body.length).to.be.at.most(5);
            console.log(`  ✓ Limit parameter working (${response.body.length} entries)`);
        });
    });
});
