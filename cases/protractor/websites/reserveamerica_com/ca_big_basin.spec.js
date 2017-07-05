/**
 * Created by Shaoke Xu on 6/25/17.
 */

var protractor = require('protractor');
var jsonfile = require('jsonfile');
var moment = require('moment');

var PageObject = require('./po');

var resultsJSON = '/automation/logs/results.json';

function windowMaximize() {
  browser.driver.manage().window().maximize();
}
windowMaximize();

describe('ca_big_basin', function () {
  var po = new PageObject();

  var results = jsonfile.readFileSync(resultsJSON);

  function pushResult(value){
    console.log("-------------------------");
    var deferred = protractor.promise.defer();
    console.log("[pushResult][step1] prepare");
//    result.then(function(value){
//      !results['BIG BASIN REDWOODS SP, CA']&&(results['BIG BASIN REDWOODS SP, CA']=[]);
//      results['BIG BASIN REDWOODS SP, CA'].push(value);
//      console.log("[pushResult][step3][success] pushed result. ", value);
//      //jsonfile.writeFileSync(resultsJSON, results);
//      return deferred.fulfill();
//    }, function(err){
//      console.log("[pushResult][step3][fail]");
//      return deferred.reject();
//    });

    setTimeout(function(){
      !results['BIG BASIN REDWOODS SP, CA']&&(results['BIG BASIN REDWOODS SP, CA']=[]);
      results['BIG BASIN REDWOODS SP, CA'].push(value);
      return deferred.fulfill();
    },0);

    return deferred.promise;
  }

  function writeResult(){
//    var deferred = protractor.promise.defer();
    console.log("===========writeResult: ", results);
    jsonfile.writeFileSync(resultsJSON, results);
//    return deferred.promise;
  }

  function newPromise(){
    var deferred = protractor.promise.defer();
    var value = arguments;
    setTimeout(function(){
      return deferred.fulfill.apply(value)
    },10);
    return deferred.promise;
  }

  function findAvailableDates(){
    var deferred = protractor.promise.defer();
    console.log("+++++++++++++++++++++++++++");
    var $dateRangeAvailability = $(po.dateRangeAvailabilityLocator);
    // waiting Date Range Avaiability to show
    browser.wait($dateRangeAvailability.isPresent(), 5*60*1000, "Cannot load 'Date Range Availability'");
    console.log("[findAvailableDates][step1] $dateRangeAvailability isPresent");
    $dateRangeAvailability.click();
    console.log("[findAvailableDates][step2] $dateRangeAvailability clicked");
    // scroll to Date Range Availablity
    browser.executeScript('arguments[0].scrollIntoView()', $dateRangeAvailability);
    console.log("[findAvailableDates][step3] scroll to $dateRangeAvailability");
    // Find all available dates
//    return $$(po.availableLocator).map(function(elm, index){
//      return elm.getAttribute('href').then(function(url){
//        return {
//          url: url
//        }
//      })
//    });

    $$(po.availableLocator).count().then(function(value){
      if(value>0){
        var list = $$(po.availableLocator).map(function(elm, index){
          return elm.getAttribute('href').then(function(url){
            return {
              url: url
            }
          })
        });
        return deferred.fulfill(list);
      }else{
        return deferred.fulfill(newPromise([]));
      }
    })

    return deferred.promise;
  }

  function action(times){
    console.log("===============================");
    console.log("[action][step1] times: ", times);
    var deferred = protractor.promise.defer();
    var next2WeeksBtn = $(po.next2WeeksLocator);
    console.log("[action][step2] find next2WeeksBtn ");
    next2WeeksBtn.click();
    console.log("[action][step3] click next2WeeksBtn");
    findAvailableDates()
    .then(function(result){
      return result;
    })
    .then(function(values){
      console.log(values);
      return pushResult(values);
    })
    .then(function(){
      console.log("[action][step4][success] times>0, do action again. times: ", times);
      console.log("===============================");
      return deferred.fulfill();
    }, function(){
      console.log("[action][step4][fail] times>0, do action again. times: ", times);
      console.log("===============================");
      return deferred.reject();
    });
    return deferred.promise;
  }

  function find(times){
    return action(times).then(function(){
      if(times>0){
        return find(--times);
      }else{
         var deferred = protractor.promise.defer();
         setTimeout(function(){
          deferred.fulfill();
         },10);
         return deferred.promise;
      }
    });
  }

  beforeAll(function () {
    browser.waitForAngularEnabled(false);
    browser.get('https://www.reserveamerica.com/camping/big-basin-redwoods-sp/r/campgroundDetails.do?contractCode=CA&parkId=120009#sr_a', 2000);
  });

  afterAll(function () {
    // add you after all
    browser.sleep(10*1000);
  });

  it('BIG BASIN REDWOODS SP, CA', function(){
    // type Arrival date
    var startDay = moment().add(2, 'days').format("MM/DD/YYYY");
    // type date
    po.$campingDate.sendKeys(startDay);
    // type length
    po.$lengthOfStay.sendKeys("1");
    // click search
    po.$searchAvailable.click();
    pushResult(findAvailableDates())
    find(5).then(function(){
      writeResult();
    });
    expect(true).toBeTruthy();
  });

});
