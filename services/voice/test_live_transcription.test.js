const request = require('supertest');
const { describe, it } = require('mocha');
const { expect } = require('chai');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');

// Test the actual running service
const BASE_URL = 'http://localhost:8001';
const WS_URL = 'ws://localhost:8001';

describe('Live Transcription with TTS Audio', () => {
    let testAudioFile = null;

    describe('Setup: Generate Test Audio', () => {
        it('should generate test audio file from text', async function() {
            this.timeout(10000);
            
            // Minimal test text to reduce API costs
            const testText = 'Hello test';
            console.log(`\n  Generating audio for: "${testText}"`);
            
            const response = await request(BASE_URL)
                .post('/synthesize')
                .send({ text: testText })
                .expect(200);
            
            expect(response.body).to.have.property('audio_bytes');
            expect(response.body).to.have.property('format', 'wav');
            
            // Save audio to temporary file
            const audioBuffer = Buffer.from(response.body.audio_bytes, 'base64');
            testAudioFile = {
                buffer: audioBuffer,
                text: testText,
                base64: response.body.audio_bytes
            };
            
            console.log(`  ✓ Generated ${audioBuffer.length} bytes of audio`);
            
            // Optional: Save to file for manual inspection
            const outputPath = path.join(__dirname, 'test_audio.wav');
            fs.writeFileSync(outputPath, audioBuffer);
            console.log(`  ✓ Saved test audio to: ${outputPath}`);
        });
    });

    describe('Live Transcription via WebSocket', () => {
        it('should transcribe pre-generated audio via WebSocket', function(done) {
            this.timeout(20000);
            
            if (!testAudioFile) {
                return done(new Error('Test audio not generated'));
            }
            
            const ws = new WebSocket(`${WS_URL}/live-transcribe`);
            let receivedStarted = false;
            let receivedTranscript = false;
            
            ws.on('open', () => {
                console.log('  ✓ WebSocket connected');
            });
            
            ws.on('message', (data) => {
                const msg = JSON.parse(data.toString());
                console.log(`  → Received: ${msg.type}`, msg.text ? `"${msg.text.substring(0, 30)}..."` : '');
                
                if (msg.type === 'started') {
                    receivedStarted = true;
                    console.log('  ✓ Live transcription started');
                    
                    // Send audio data
                    sendAudioData(ws, testAudioFile.buffer);
                    
                } else if (msg.type === 'partial' || msg.type === 'final') {
                    receivedTranscript = true;
                    console.log(`  ✓ Received ${msg.type} transcript`);
                    
                } else if (msg.type === 'stopped') {
                    console.log('  ✓ Session stopped');
                    ws.close();
                    
                } else if (msg.type === 'error') {
                    console.error(`  ✗ Error: ${msg.error}`);
                    ws.close();
                    done(new Error(msg.error));
                }
            });
            
            ws.on('close', () => {
                // Minimal validation - just verify API is working
                try {
                    expect(receivedStarted).to.be.true;
                    expect(receivedTranscript).to.be.true;
                    
                    console.log('  ✓ Live transcription API working');
                    done();
                } catch (err) {
                    done(err);
                }
            });
            
            ws.on('error', (err) => {
                console.error(`  ✗ WebSocket error: ${err.message}`);
                done(err);
            });
        });
    });

    describe('Compare with Regular Transcription', () => {
        it('should support both batch and live transcription', async function() {
            this.timeout(15000);
            
            if (!testAudioFile) {
                throw new Error('Test audio not generated');
            }
            
            // Just verify both endpoints work - don't compare results to save API costs
            
            // Batch transcription
            const batchResponse = await request(BASE_URL)
                .post('/transcribe')
                .send({ 
                    audio_bytes: testAudioFile.base64,
                    format: 'wav'
                })
                .expect(200);
            
            expect(batchResponse.body).to.have.property('transcript');
            console.log(`  ✓ Batch transcription API working`);
            
            // Live transcription - minimal check
            const liveWorked = await new Promise((resolve, reject) => {
                const ws = new WebSocket(`${WS_URL}/live-transcribe`);
                let gotTranscript = false;
                
                ws.on('message', (data) => {
                    const msg = JSON.parse(data.toString());
                    
                    if (msg.type === 'started') {
                        sendAudioData(ws, testAudioFile.buffer);
                    } else if (msg.type === 'partial' || msg.type === 'final') {
                        gotTranscript = true;
                        setTimeout(() => {
                            ws.send(JSON.stringify({ type: 'stop' }));
                        }, 500);
                    } else if (msg.type === 'stopped') {
                        ws.close();
                    }
                });
                
                ws.on('close', () => resolve(gotTranscript));
                ws.on('error', () => resolve(false));
                
                setTimeout(() => {
                    ws.close();
                    resolve(gotTranscript);
                }, 10000);
            });
            
            expect(liveWorked).to.be.true;
            console.log('  ✓ Live transcription API working');
            console.log('  ✓ Both transcription methods functional');
        });
    });
});

// Helper function to send audio data
function sendAudioData(ws, wavBuffer) {
    try {
        // Extract PCM data from WAV
        const pcmData = extractPCMFromWAV(wavBuffer);
        console.log(`  ✓ Extracted ${pcmData.length} bytes of PCM data`);
        
        // Send all at once (in real scenario, would stream in chunks)
        ws.send(pcmData);
        console.log('  ✓ Audio data sent');
        
        // Give it time to process then stop
        setTimeout(() => {
            ws.send(JSON.stringify({ type: 'stop' }));
        }, 3000);
        
    } catch (err) {
        console.error(`  ✗ Error sending audio: ${err.message}`);
    }
}

// Helper to extract PCM16 data from WAV file
function extractPCMFromWAV(wavBuffer) {
    // WAV header is 44 bytes
    // But we need to properly parse to find data chunk
    let offset = 12; // Skip RIFF header
    
    while (offset < wavBuffer.length) {
        const chunkId = wavBuffer.toString('ascii', offset, offset + 4);
        const chunkSize = wavBuffer.readUInt32LE(offset + 4);
        
        if (chunkId === 'data') {
            // Found data chunk, return the PCM data
            return wavBuffer.slice(offset + 8, offset + 8 + chunkSize);
        }
        
        // Move to next chunk
        offset += 8 + chunkSize;
    }
    
    // Fallback: assume standard 44-byte header
    return wavBuffer.slice(44);
}
