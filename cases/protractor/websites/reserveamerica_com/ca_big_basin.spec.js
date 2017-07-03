/**
 * Created by Shaoke Xu on 6/25/17.
 */
var PageObject = require('./po');
var jsonfile = require('jsonfile');
var resultsJSON = '/automation/logs/results.json';

function windowMaximize() {
  browser.driver.manage().window().maximize();
}
windowMaximize();

describe('ca_big_basin', function () {
  var po = new PageObject();

  var results = jsonfile.readFileSync(resultsJSON);

  beforeAll(function () {
    browser.waitForAngularEnabled(false);
    browser.get('https://www.reserveamerica.com/camping/big-basin-redwoods-sp/r/campgroundDetails.do?contractCode=CA&parkId=120009#sr_a', 2000);
  });

  afterAll(function () {
    // add you after all
    browser.sleep(10*1000);
  });

  function findAvailableDates(){
    var $dateRangeAvailability = $(po.dateRangeAvailabilityLocator);
    // waiting Date Range Avaiability to show
    browser.wait($dateRangeAvailability.isPresent(), 5*60*1000, "Cannot load 'Date Range Availability'");
    $dateRangeAvailability.click();
    // scroll to Date Range Availablity
    browser.executeScript('arguments[0].scrollIntoView()', $dateRangeAvailability);
    // Find all available dates
    var $$sunAvailable = $$(po.sunAvailableLocator);
    var result = [];
    $$sunAvailable.map(function(elm, index){
      result.push({
        url: "https://www.reserveamerica.com"+elm.getAttribute('href')
      });
    });

    console.log("result: ", result);
    return result;
  }

  it('open reserve america', function(){
    // type Arrival date
    po.$campingDate.sendKeys("07/01/2017");
    po.$lengthOfStay.sendKeys("1");
    po.$searchAvailable.click();

    // Find all availability date and save to JSON file
    var dates = findAvailableDates();

    results["BIG BASIN REDWOODS SP, CA"] = dates;

    console.log("results: ", results);

    jsonfile.writeFileSync(resultsJSON, {
      "test":true
    });

    expect(true).toBeTruthy();
  });

});
