/**
 * Created by Shaoke Xu on 6/25/17.
 */

/**
 * this is config file for protractor
 *
 * @link https://github.com/angular/protractor/blob/master/docs/referenceConf.js
 **/
var conf = {};
var chalk = require('chalk');
var jasmineReporters = require('jasmine-reporters');
var path = require('path');
var reportFolderPath = path.resolve(__dirname, '../../reports/');
var HtmlScreenshotReporter = require('protractor-jasmine2-screenshot-reporter');

var junitReporter = new jasmineReporters.JUnitXmlReporter({
  consolidateAll: true,
  savePath: reportFolderPath,
  filePrefix: 'chrome-uat-reports.xml'
});
var htmlReporter = new HtmlScreenshotReporter({
  dest: reportFolderPath,
  filename: 'chrome-uat-reports.html',
  captureOnlyFailedSpecs: true,
  reportOnlyFailedSpecs: false,
  showSummary: true,
  showQuickLinks: true,
  pathBuilder: function(currentSpec, suites, browserCapabilities) {
    // will return screenshots/chrome/your-spec-name.png
    return 'screenshots/' + browserCapabilities.get('browserName') + '/' + currentSpec.fullName.replace(/\[.+\]/g, '-');
  }
});

conf.htmlReporter = htmlReporter;
conf.junitReporter = junitReporter;
conf.config = {
  // location of the Selenium JAR file and chromedriver, use these if you installed protractor locally
  // seleniumServerJar: '../node_modules/protractor/node_modules/webdriver-manager/selenium/selenium-server-standalone-3.4.0.jar',
  seleniumAddress: 'http://localhost:4444/wd/hub',

  capabilities: {
    'browserName': 'chrome',
    chromeOptions: {
      args: ['--no-sandbox']
    },
    // marionette: true,
    acceptSslCerts: true,
    trustAllSSLCertificates: true,
    // shardTestFiles: false,
    // maxInstances: 1,
    "loggingPrefs": {"driver": "ALL", "server": "OFF", "browser": "ALL"}
    // "loggingPrefs": {"driver": "INFO", "server": "OFF", "browser": "INFO"}
    // "loggingPrefs": {"driver": "WARNING", "server": "OFF", "browser": "SEVERE"}
  },

  jasmineNodeOpts: {
    defaultTimeoutInterval: 600000,
    allScriptsTimeout: 30000
  },

  beforeLaunch: function() {
    return new Promise(function(resolve){
      htmlReporter.beforeLaunch(resolve);
    });
  },

  onPrepare: function () {
    browser.waitForAngularEnabled(false);
    browser.manage().timeouts().setScriptTimeout(60000);
    jasmine.DEFAULT_TIMEOUT_INTERVAL = 60000;
    jasmine.getEnv().addReporter(conf.junitReporter);
    jasmine.getEnv().addReporter(conf.htmlReporter);
  },

  afterLaunch: function(exitCode) {
    return new Promise(function(resolve){
      htmlReporter.afterLaunch(resolve.bind(this, exitCode));
    });
  },

  // testing framework, jasmine is the default
  framework: 'jasmine',
  SELENIUM_PROMISE_MANAGER: 1,
  specs: ['**/*.spec.js'],
};

module.exports = conf;
