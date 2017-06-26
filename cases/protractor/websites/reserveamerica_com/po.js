/**
 * Created by Shaoke Xu on 6/25/17.
 */
var protractor = require('protractor');
var EC = protractor.ExpectedConditions;
function PageObject(){
  this.$campingDate = $("#campingDate");
  this.$lengthOfStay = $("#lengthOfStay");
  this.$searchAvailable = $('#search_avail');
  this.$calendarViewSwitch = $('#calendar_view_switch');
  this.$calendar = $('#calendar');
  this.$next2Weeks = $('#calendar .weeknav.week2');
}

module.exports = PageObject;
