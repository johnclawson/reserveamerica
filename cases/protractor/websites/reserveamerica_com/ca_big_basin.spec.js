/**
 * Created by Shaoke Xu on 6/25/17.
 */
var PageObject = require('./po');

function windowMaximize() {
  browser.driver.manage().window().maximize();
}
windowMaximize();

describe('ca_big_basin', function () {
  var po = new PageObject();

  beforeAll(function () {
    browser.waitForAngularEnabled(false);
    browser.get('https://www.reserveamerica.com/camping/big-basin-redwoods-sp/r/campgroundDetails.do?contractCode=CA&parkId=120009#sr_a', 2000);
  });

  afterAll(function () {
    // add you after all
    browser.sleep(2000);
  });

  it('open reserve america', function(){
    expect(po.$next2Weeks.isPresent()).toBeTruthy();
  });

});
