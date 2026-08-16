#include <SPI.h>
#include <SD.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 16
#define SD_CS 4

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

File reportFile;

bool reportMode = false;
char lineBuffer[128];
int bufferIndex = 0;
int sessionNumber = 1;

void setup() {

  Serial.begin(115200);

  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  display.setCursor(0, 0);
  display.println("SYSTEM READY");
  display.display();

  if (!SD.begin(SD_CS)) {
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("SD FAILED!");
    display.display();
    while (true);
  }
}

void loop() {

  while (Serial.available()) {

    char c = Serial.read();

    if (c == '\n') {
      lineBuffer[bufferIndex] = '\0';
      processLine(lineBuffer);
      bufferIndex = 0;
    }
    else {
      if (bufferIndex < sizeof(lineBuffer) - 1) {
        lineBuffer[bufferIndex++] = c;
      }
    }
  }
}

void processLine(char* line) {

  if (strcmp(line, "START_REPORT") == 0) {

    reportMode = true;

    char filename[20];
    sprintf(filename, "SESSION%d.TXT", sessionNumber++);

    reportFile = SD.open(filename, FILE_WRITE);

    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("Saving Report...");
    display.display();

    return;
  }

  if (strcmp(line, "END_REPORT") == 0) {

    reportMode = false;

    if (reportFile) {
      reportFile.flush();
      reportFile.close();
    }

    display.clearDisplay();
    display.setCursor(0, 0);
    display.println("Report Saved!");
    display.display();

    return;
  }

  if (reportMode) {

    if (reportFile) {
      reportFile.println(line);
    }
  }
  else {

    display.clearDisplay();
    display.setCursor(0, 0);
    display.println(line);
    display.display();
  }
}